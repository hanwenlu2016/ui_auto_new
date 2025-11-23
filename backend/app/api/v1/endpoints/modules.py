from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.user import User
from app.schemas.module import Module as ModuleSchema, ModuleCreate, ModuleUpdate
from app.services.module_service import module_service

router = APIRouter()

@router.get("/", response_model=List[ModuleSchema])
async def read_modules(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    project_id: int = None,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve modules.
    """
    filters = {}
    if project_id:
        filters["project_id"] = project_id
        
    modules = await module_service.get_multi(db, skip=skip, limit=limit, filters=filters)
    return modules

@router.post("/", response_model=ModuleSchema)
async def create_module(
    *,
    db: AsyncSession = Depends(deps.get_db),
    module_in: ModuleCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new module.
    """
    module = await module_service.create(db, obj_in=module_in)
    return module

@router.get("/{module_id}", response_model=ModuleSchema)
async def read_module(
    *,
    db: AsyncSession = Depends(deps.get_db),
    module_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get module by ID.
    """
    module = await module_service.get(db, id=module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return module

@router.put("/{module_id}", response_model=ModuleSchema)
async def update_module(
    *,
    db: AsyncSession = Depends(deps.get_db),
    module_id: int,
    module_in: ModuleUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update module.
    """
    module = await module_service.get(db, id=module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    module = await module_service.update(db, db_obj=module, obj_in=module_in)
    return module

@router.delete("/{module_id}", response_model=ModuleSchema)
async def delete_module(
    *,
    db: AsyncSession = Depends(deps.get_db),
    module_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete module.
    """
    module = await module_service.get(db, id=module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
        
    await module_service.remove(db, id=module_id)
    return module
