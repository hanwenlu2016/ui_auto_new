from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.user import User
from app.schemas.suite import TestSuite as TestSuiteSchema, TestSuiteCreate, TestSuiteUpdate
from app.services.suite_service import suite_service

router = APIRouter()

@router.get("/", response_model=List[TestSuiteSchema])
async def read_test_suites(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    project_id: int = None,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve test suites.
    """
    filters = {}
    if project_id:
        filters["project_id"] = project_id
        
    test_suites = await suite_service.get_multi(db, skip=skip, limit=limit, filters=filters)
    return test_suites

@router.post("/", response_model=TestSuiteSchema)
async def create_test_suite(
    *,
    db: AsyncSession = Depends(deps.get_db),
    test_suite_in: TestSuiteCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new test suite.
    """
    test_suite = await suite_service.create(db, obj_in=test_suite_in, creator_id=current_user.id, updater_id=current_user.id)
    return test_suite

@router.get("/{suite_id}", response_model=TestSuiteSchema)
async def read_test_suite(
    *,
    db: AsyncSession = Depends(deps.get_db),
    suite_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get test suite by ID.
    """
    test_suite = await suite_service.get(db, id=suite_id)
    if not test_suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    return test_suite

@router.put("/{suite_id}", response_model=TestSuiteSchema)
async def update_test_suite(
    *,
    db: AsyncSession = Depends(deps.get_db),
    suite_id: int,
    test_suite_in: TestSuiteUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update test suite.
    """
    test_suite = await suite_service.get(db, id=suite_id)
    if not test_suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    
    test_suite = await suite_service.update(db, db_obj=test_suite, obj_in=test_suite_in, updater_id=current_user.id)
    return test_suite

@router.delete("/{suite_id}", response_model=TestSuiteSchema)
async def delete_test_suite(
    *,
    db: AsyncSession = Depends(deps.get_db),
    suite_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete test suite.
    """
    test_suite = await suite_service.get(db, id=suite_id)
    if not test_suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
        
    await suite_service.remove(db, id=suite_id)
    return test_suite
