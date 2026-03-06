from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import Dict, Any, List

from app.api import deps
from app.models.project import Project
from app.models.case import TestCase
from app.models.report import TestReport

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(deps.get_db)) -> Dict[str, Any]:
    project_count_res = await db.execute(select(func.count(Project.id)))
    project_count = project_count_res.scalar_one_or_none() or 0
    
    case_count_res = await db.execute(select(func.count(TestCase.id)))
    case_count = case_count_res.scalar_one_or_none() or 0
    
    total_reports_res = await db.execute(select(func.count(TestReport.id)))
    total_reports = total_reports_res.scalar_one_or_none() or 0
    
    success_reports_res = await db.execute(select(func.count(TestReport.id)).where(TestReport.status == 'success'))
    success_reports = success_reports_res.scalar_one_or_none() or 0
    
    # Calculate success rate
    success_rate = 0
    if total_reports > 0:
        success_rate = round((success_reports / total_reports) * 100)
        
    return {
        "projects": project_count,
        "cases": case_count,
        "executions": total_reports,
        "success_rate": f"{success_rate}%"
    }

@router.get("/activities")
async def get_recent_activities(db: AsyncSession = Depends(deps.get_db), limit: int = 5) -> List[Dict[str, Any]]:
    # Get most recent reports as activities
    # Need to eager load test_case to access it properly if it's async, or select directly
    # For simplicity, we can just select the necessary fields using join
    query = select(TestReport.id, TestReport.status, TestReport.created_at, TestReport.report_path, TestCase.name.label("case_name"))\
        .outerjoin(TestCase, TestReport.test_case_id == TestCase.id)\
        .order_by(TestReport.created_at.desc())\
        .limit(limit)
        
    result = await db.execute(query)
    rows = result.all()
    
    import os
    activities = []
    for row in rows:
        report_url = None
        if row.report_path and "allure-reports" in row.report_path:
            folder_name = os.path.basename(row.report_path)
            report_url = f"/reports/{folder_name}/index.html"
            
        activities.append({
            "id": row.id,
            "desc": f"执行了测试用例: {row.case_name if row.case_name else '未知'}",
            "status": row.status,
            "time": row.created_at.isoformat() if row.created_at else None,
            "url": report_url
        })
        
    return activities
