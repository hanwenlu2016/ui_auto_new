from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.user import User
from app.worker import run_test_case_task, run_test_suite_task
from celery.result import AsyncResult
from app.core.celery_app import celery_app
from app.core.config import settings

router = APIRouter()

class ExecutionOptions(BaseModel):
    headless: Optional[bool] = None  # None means use config default
    browser_type: Optional[str] = None  # None means use config default

@router.post("/cases/{case_id}/run")
async def run_test_case(
    *,
    db: AsyncSession = Depends(deps.get_db),
    case_id: int,
    options: Optional[ExecutionOptions] = None,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Run a specific test case asynchronously.
    """
    if options is None:
        options = ExecutionOptions()
    
    # Use config defaults if not specified
    headless = options.headless if options.headless is not None else settings.BROWSER_HEADLESS
    browser_type = options.browser_type if options.browser_type else settings.BROWSER_TYPE
    
    task = run_test_case_task.delay(case_id, headless, browser_type, current_user.id)
    return {
        "task_id": task.id, 
        "status": "started",
        "message": "测试已启动,请到测试报告页面查看执行结果"
    }

@router.post("/suites/{suite_id}/run")
async def run_test_suite(
    *,
    db: AsyncSession = Depends(deps.get_db),
    suite_id: int,
    options: Optional[ExecutionOptions] = None,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Run a specific test suite asynchronously.
    """
    if options is None:
        options = ExecutionOptions()
    
    # Use config defaults if not specified
    headless = options.headless if options.headless is not None else settings.BROWSER_HEADLESS
    browser_type = options.browser_type if options.browser_type else settings.BROWSER_TYPE
    
    task = run_test_suite_task.delay(suite_id, headless, browser_type, current_user.id)
    return {
        "task_id": task.id, 
        "status": "started",
        "message": "测试套件已启动,请到测试报告页面查看执行结果"
    }

@router.get("/status/{task_id}")
async def get_task_status(task_id: str) -> Any:
    """
    Get the status of a background task.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }
