import asyncio
import logging
import nest_asyncio
from app.core.celery_app import celery_app
from app.services.runner import TestRunner
from app.services.report_service import ReportService
from app.db.session import AsyncSessionLocal

# Allow nested event loops for Celery workers
nest_asyncio.apply()

logger = logging.getLogger(__name__)

@celery_app.task(acks_late=True)
def run_test_case_task(case_id: int, headless: bool = True, browser_type: str = "chromium", executor_id: int = None):
    logger.info(f"Starting test case execution for case_id={case_id}, headless={headless}, browser={browser_type}, executor={executor_id}")
    
    async def _run():
        async with AsyncSessionLocal() as db:
            runner = TestRunner(db)
            result = await runner.run_test_case(case_id, headless=headless, browser_type=browser_type)
            logger.info(f"Test case {case_id} completed. Success: {result.get('success')}")
            
            # Generate Allure report
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
                    executor_id=executor_id
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

@celery_app.task(acks_late=True)
def run_test_suite_task(suite_id: int, headless: bool = True, browser_type: str = "chromium", executor_id: int = None):
    logger.info(f"Starting test suite execution for suite_id={suite_id}, headless={headless}, browser={browser_type}, executor={executor_id}")
    
    async def run_single_case(case_id: int, case_name: str):
        """Run a single test case in its own DB session"""
        async with AsyncSessionLocal() as db:
            runner = TestRunner(db)
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
                    report_name=suite_name  # Use suite name for report folder
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
