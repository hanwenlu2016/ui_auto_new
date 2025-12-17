from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.user import User
from app.schemas.case import TestCase as TestCaseSchema, TestCaseCreate, TestCaseUpdate
from app.services.case_service import case_service

router = APIRouter()

@router.get("/", response_model=List[TestCaseSchema])
async def read_test_cases(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    module_id: int = None,
    project_id: int = None,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve test cases.
    """
    filters = {}
    if module_id:
        filters["module_id"] = module_id
    if project_id:
        filters["project_id"] = project_id
        
    test_cases = await case_service.get_multi(db, skip=skip, limit=limit, filters=filters)
    return test_cases

@router.post("/", response_model=TestCaseSchema)
async def create_test_case(
    *,
    db: AsyncSession = Depends(deps.get_db),
    test_case_in: TestCaseCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new test case.
    """
    test_case = await case_service.create(db, obj_in=test_case_in, creator_id=current_user.id, updater_id=current_user.id)
    return test_case

@router.get("/{case_id}", response_model=TestCaseSchema)
async def read_test_case(
    *,
    db: AsyncSession = Depends(deps.get_db),
    case_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get test case by ID.
    """
    test_case = await case_service.get(db, id=case_id)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    return test_case

@router.put("/{case_id}", response_model=TestCaseSchema)
async def update_test_case(
    *,
    db: AsyncSession = Depends(deps.get_db),
    case_id: int,
    test_case_in: TestCaseUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update test case.
    """
    test_case = await case_service.get(db, id=case_id)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    test_case = await case_service.update(db, db_obj=test_case, obj_in=test_case_in, updater_id=current_user.id)
    return test_case

@router.delete("/{case_id}", response_model=TestCaseSchema)
async def delete_test_case(
    *,
    db: AsyncSession = Depends(deps.get_db),
    case_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete test case.
    """
    test_case = await case_service.get(db, id=case_id)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
        
    await case_service.remove(db, id=case_id)
    return test_case
