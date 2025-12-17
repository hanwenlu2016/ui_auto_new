"""
Celery Worker 任务定义模块

本模块定义了所有异步执行的 Celery 任务：
1. run_test_case_task: 执行单个测试用例
2. run_test_suite_task: 并发执行测试套件中的所有用例

任务执行流程：
- 接收来自 API 的任务请求
- 在独立的数据库会话中执行测试
- 生成 Allure 测试报告
- 返回执行结果
"""
import asyncio
import nest_asyncio
from app.core.celery_app import celery_app
from app.services.runner import TestRunner
from app.services.report_service import ReportService
from app.db.session import AsyncSessionLocal

# 初始化日志系统
from app.core.logger import logger

# 允许嵌套事件循环 - Celery worker 需要
nest_asyncio.apply()

@celery_app.task(acks_late=True)
def run_test_case_task(case_id: int, headless: bool = True, browser_type: str = "chromium", executor_id: int = None):
    """
    执行单个测试用例的 Celery 任务
    """
    import tempfile
    import shutil
    import uuid
    import os
    
    logger.info(f"Starting test case execution for case_id={case_id}, headless={headless}, browser={browser_type}, executor={executor_id}")
    
    # Create a unique temporary directory for this execution
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_results_dir = os.path.join(base_dir, "temp_results", f"case_{case_id}_{uuid.uuid4()}")
    os.makedirs(temp_results_dir, exist_ok=True)
    
    async def _run():
        async with AsyncSessionLocal() as db:
            # Initialize with temp results dir
            runner = TestRunner(db, results_dir=temp_results_dir)
            
            result = await runner.run_test_case(case_id, headless=headless, browser_type=browser_type)
            logger.info(f"Test case {case_id} completed. Success: {result.get('success')}")
            
            # Generate Allure report using temp results dir
            try:
                report_service = ReportService(db)
                status = "success" if result.get('success') else "failure"
                error_msg = result.get('error')
                
                report = await report_service.generate_allure_report(
                    test_case_id=case_id,
                    browser_type=browser_type,
                    headless=headless,
                    status=status,
                    error_message=error_msg,
                    executor_id=executor_id,
                    results_dir=temp_results_dir  # Pass temp dir
                )
                logger.info(f"Report generated: {report.report_path}")
                result['report_id'] = report.id
                result['report_path'] = report.report_path
            except Exception as e:
                logger.error(f"Failed to generate report: {e}", exc_info=True)
                result['report_error'] = str(e)
            
            return result
    
    try:
        result = asyncio.run(_run())
        return result
    except Exception as e:
        logger.error(f"Test case {case_id} failed with error: {e}", exc_info=True)
        raise
    finally:
        # cleanup temp directory
        if os.path.exists(temp_results_dir):
            try:
                shutil.rmtree(temp_results_dir, ignore_errors=True)
                logger.info(f"Cleaned up temp results directory: {temp_results_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir {temp_results_dir}: {e}")

@celery_app.task(acks_late=True)
def run_test_suite_task(suite_id: int, headless: bool = True, browser_type: str = "chromium", executor_id: int = None):
    """
    并发执行测试套件中所有用例的 Celery 任务
    """
    import tempfile
    import shutil
    import uuid
    import os
    
    logger.info(f"Starting test suite execution for suite_id={suite_id}, headless={headless}, browser={browser_type}, executor={executor_id}")
    
    # Create a unique temporary directory for this suite execution
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_results_dir = os.path.join(base_dir, "temp_results", f"suite_{suite_id}_{uuid.uuid4()}")
    os.makedirs(temp_results_dir, exist_ok=True)
    
    async def run_single_case(case_id: int, case_name: str):
        """Run a single test case in its own DB session"""
        async with AsyncSessionLocal() as db:
            # Initialize with same temp results dir (assuming suite results should be aggregated)
            # Actually, concurrent writes to same dir might be an issue for some tools, but Allure handles multiple json files fine.
            # Runner generates UUID-based filenames, so it should be safe.
            runner = TestRunner(db, results_dir=temp_results_dir)
            try:
                logger.info(f"Running test case {case_id} ({case_name}) in suite {suite_id}")
                result = await runner.run_test_case(case_id, headless=headless, browser_type=browser_type)
                return {
                    "case_id": case_id,
                    "case_name": case_name,
                    "result": result,
                    "success": result.get("success", False),
                    "error": result.get("error")
                }
            except Exception as e:
                logger.error(f"Failed to run test case {case_id}: {e}")
                return {
                    "case_id": case_id,
                    "case_name": case_name,
                    "result": None,
                    "success": False,
                    "error": str(e)
                }

    async def _run():
        async with AsyncSessionLocal() as db:
            # Fetch suite and its test cases
            from app.services.suite_service import suite_service
            suite = await suite_service.get(db, id=suite_id)
            if not suite:
                return {"success": False, "error": "Test suite not found"}
            
            if not suite.test_cases:
                return {"success": False, "error": "Test suite has no test cases"}
            
            suite_name = suite.name
            test_cases = suite.test_cases
            
        # Run test cases in parallel
        # Note: We use separate sessions for each case, so we don't need the main db session here
        tasks = [run_single_case(tc.id, tc.name) for tc in test_cases]
        results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for r in results if r["success"])
        failure_count = len(results) - success_count
        
        # Generate consolidated Allure report
        async with AsyncSessionLocal() as db:
            try:
                report_service = ReportService(db)
                overall_status = "success" if failure_count == 0 else "failure"
                
                report = await report_service.generate_allure_report(
                    test_suite_id=suite_id,
                    browser_type=browser_type,
                    headless=headless,
                    status=overall_status,
                    executor_id=executor_id,
                    report_name=suite_name,  # Use suite name for report folder
                    results_dir=temp_results_dir # Pass temp dir
                )
                logger.info(f"Suite report generated: {report.report_path}")
                
                return {
                    "success": True,
                    "suite_id": suite_id,
                    "total_cases": len(results),
                    "passed": success_count,
                    "failed": failure_count,
                    "results": results,
                    "report_id": report.id,
                    "report_path": report.report_path
                }
            except Exception as e:
                logger.error(f"Failed to generate suite report: {e}", exc_info=True)
                return {
                    "success": False, 
                    "error": f"Tests finished but report generation failed: {e}",
                    "results": results
                }

    try:
        result = asyncio.run(_run())
        return result
    except Exception as e:
        logger.error(f"Test suite {suite_id} failed with error: {e}", exc_info=True)
        raise
    finally:
        # cleanup
        if os.path.exists(temp_results_dir):
            try:
                shutil.rmtree(temp_results_dir, ignore_errors=True)
                logger.info(f"Cleaned up temp results directory: {temp_results_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir {temp_results_dir}: {e}")
