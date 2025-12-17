from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.schemas.page import Page, PageCreate, PageUpdate
from app.services.page_service import PageService
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[Page])
async def read_pages(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    module_id: int = None,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve pages.
    """
    service = PageService(db)
    if module_id:
        return await service.get_by_module(db, module_id)
    return await service.get_multi(db, skip=skip, limit=limit)

@router.post("/", response_model=Page)
async def create_page(
    *,
    db: AsyncSession = Depends(deps.get_db),
    page_in: PageCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new page.
    """
    service = PageService(db)
    return await service.create(db, obj_in=page_in, creator_id=current_user.id, updater_id=current_user.id)

@router.put("/{id}", response_model=Page)
async def update_page(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: int,
    page_in: PageUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update a page.
    """
    service = PageService(db)
    page = await service.get(db, id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return await service.update(db, db_obj=page, obj_in=page_in, updater_id=current_user.id)

@router.delete("/{id}", response_model=Page)
async def delete_page(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete a page.
    """
    service = PageService(db)
    page = await service.get(db, id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return await service.remove(db, id=id)
