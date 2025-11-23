"""
测试报告服务模块

本模块负责 Allure 测试报告的生成和管理：
1. 调用 Allure CLI 生成 HTML 测试报告
2. 管理报告的数据库记录（CRUD 操作）
3. 物理删除报告文件和目录
4. 支持自定义报告名称（用于测试套件）

报告存储路径：backend/allure-reports/
结果文件路径：backend/allure-results/
"""
import os
import subprocess
import shutil
from typing import List, Dict, Optional
from sqlalchemy import select
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.report import TestReport
from app.schemas.report import TestReportCreate

# 使用全局日志系统
from app.core.logger import logger

class ReportService:
    """测试报告服务类 - 负责 Allure 报告的生成和管理"""
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        初始化报告服务
        
        Args:
            db: 异步数据库会话（可选）
        """
        self.db = db
        # 计算报告和结果目录路径（backend/allure-reports 和 backend/allure-results）
        # report_service.py 位于 backend/app/services/，需要向上3级
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.results_dir = os.path.join(base_dir, "allure-results")
        self.reports_dir = os.path.join(base_dir, "allure-reports")
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

    async def generate_allure_report(
        self,
        test_case_id: Optional[int] = None,
        test_suite_id: Optional[int] = None,
        browser_type: str = "chromium",
        headless: bool = True,
        status: str = "success",
        error_message: Optional[str] = None,
        executor_id: Optional[int] = None,
        report_name: Optional[str] = None
    ) -> TestReport:
        """Generate Allure report and save to database."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not report_name:
            report_name = f"report_{timestamp}"
            if test_case_id:
                report_name = f"case_{test_case_id}_{timestamp}"
            elif test_suite_id:
                report_name = f"suite_{test_suite_id}_{timestamp}"
        else:
            # Sanitize report name to be filesystem friendly
            safe_name = "".join([c for c in report_name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')
            report_name = f"{safe_name}_{timestamp}"
        
        report_path = os.path.join(self.reports_dir, report_name)
        
        try:
            subprocess.run(
                ["allure", "generate", self.results_dir, "-o", report_path, "--clean"],
                check=True,
                timeout=30
            )
            logger.info(f"Allure report generated: {report_path}")
        except FileNotFoundError:
            logger.warning("Allure CLI not found, skipping HTML report generation")
            report_path = "allure_not_installed"
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            report_path = f"error: {str(e)}"
        
        # Save to database if db session provided
        if self.db:
            report_data = TestReportCreate(
                test_case_id=test_case_id,
                test_suite_id=test_suite_id,
                executor_id=executor_id,
                report_path=report_path,
                status=status,
                browser_type=browser_type,
                headless=headless,
                error_message=error_message
            )
            
            db_report = TestReport(**report_data.model_dump())
            self.db.add(db_report)
            await self.db.commit()
            await self.db.refresh(db_report)
            return db_report
        
        # Return a mock report if no db
        return TestReport(
            id=0,
            test_case_id=test_case_id,
            test_suite_id=test_suite_id,
            report_path=report_path,
            status=status,
            browser_type=browser_type,
            headless=headless,
            error_message=error_message,
            created_at=datetime.now()
        )

    # CRUD helper methods for report management
    async def get_reports(self, skip: int = 0, limit: int = 100) -> List[TestReport]:
        stmt = select(TestReport).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_report(self, report_id: int) -> Optional[TestReport]:
        return await self.db.get(TestReport, report_id)

    async def delete_report(self, report: TestReport) -> None:
        # Delete the Allure report folder if it exists
        if report.report_path:
            # Ensure we are deleting a directory within our reports_dir to be safe
            # (Basic safety check, though report_path should be trusted from DB)
            if os.path.exists(report.report_path):
                if os.path.isdir(report.report_path):
                    try:
                        logger.info(f"Deleting report directory: {report.report_path}")
                        shutil.rmtree(report.report_path)
                        logger.info(f"Successfully deleted report directory: {report.report_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete report folder {report.report_path}: {e}")
                        # Re-raise exception to ensure transaction is rolled back (or at least API fails)
                        # and user is notified that file deletion failed.
                        raise e
                else:
                    logger.warning(f"Report path exists but is not a directory: {report.report_path}")
            else:
                logger.warning(f"Report path does not exist, skipping file deletion: {report.report_path}")
        else:
            logger.warning("Report path is empty, skipping file deletion")
        await self.db.delete(report)
        await self.db.commit()

    def generate_report(self) -> str:
        """Legacy method for backward compatibility."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.reports_dir, timestamp)
        
        try:
            subprocess.run(["allure", "generate", self.results_dir, "-o", report_path, "--clean"], check=True)
            return timestamp
        except FileNotFoundError:
            raise Exception("Allure command line tool not found. Please install allure.")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to generate report: {e}")

    def list_reports(self) -> List[Dict[str, str]]:
        reports = []
        if not os.path.exists(self.reports_dir):
            return reports
            
        for name in os.listdir(self.reports_dir):
            path = os.path.join(self.reports_dir, name)
            if os.path.isdir(path):
                reports.append({
                    "name": name,
                    "path": f"/reports/{name}/index.html",
                    "created_at": datetime.fromtimestamp(os.path.getctime(path)).isoformat()
                })
        
        reports.sort(key=lambda x: x["created_at"], reverse=True)
        return reports

    def delete_report_legacy(self, report_name: str):
        path = os.path.join(self.reports_dir, report_name)
        if os.path.exists(path):
            shutil.rmtree(path)
