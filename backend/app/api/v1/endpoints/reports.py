from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import os

from app.api import deps
from app.models.report import TestReport as TestReportModel
from app.models.user import User
from app.schemas.report import TestReportWithDetails, TestReport
from app.services.report_service import ReportService

router = APIRouter()

@router.get("/", response_model=List[TestReportWithDetails])
async def list_reports(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    """返回当前用户可见的所有报告列表"""
    service = ReportService(db)
    reports = await service.get_reports(skip=skip, limit=limit)
    # enrich with test case name and executor name
    # enrich with test case name and executor name
    result = []
    for r in reports:
        case_name = None
        if r.test_case_id:
            from app.models.case import TestCase
            tc = await db.get(TestCase, r.test_case_id)
            case_name = tc.name if tc else None
        elif r.test_suite_id:
            from app.models.suite import TestSuite
            ts = await db.get(TestSuite, r.test_suite_id)
            case_name = f"[套件] {ts.name}" if ts else None
            
        executor_name = None
        if r.executor_id:
            from app.models.user import User as UserModel
            user = await db.get(UserModel, r.executor_id)
            executor_name = user.full_name or user.email
            
        # Safely convert SQLAlchemy model to Pydantic model first
        base_report = TestReport.model_validate(r)
        
        # Compute relative report URL
        report_url = None
        if r.report_path and "allure-reports" in r.report_path:
            # Extract the folder name from the absolute path
            # e.g. /path/to/allure-reports/report_2025... -> /reports/report_2025.../index.html
            folder_name = os.path.basename(r.report_path)
            report_url = f"/reports/{folder_name}/index.html"
            
        result.append(TestReportWithDetails(
            **base_report.model_dump(), 
            test_case_name=case_name, 
            executor_name=executor_name,
            report_url=report_url
        ))
    return result
    
@router.delete("/{report_id}", response_model=TestReport)
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """删除报告记录并删除对应的 Allure 报告文件"""
    service = ReportService(db)
    report = await service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    # Only executor or admin can delete
    if report.executor_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="没有权限删除此报告")
    await service.delete_report(report)
    return report
