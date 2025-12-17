from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.user import User
from app.schemas.element import PageElement as PageElementSchema, PageElementCreate, PageElementUpdate
from app.services.element_service import element_service

router = APIRouter()

@router.get("/", response_model=List[PageElementSchema])
async def read_page_elements(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    module_id: int = None,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve page elements.
    """
    filters = {}
    if module_id:
        filters["module_id"] = module_id
        
    page_elements = await element_service.get_multi(db, skip=skip, limit=limit, filters=filters)
    return page_elements

@router.post("/", response_model=PageElementSchema)
async def create_page_element(
    *,
    db: AsyncSession = Depends(deps.get_db),
    page_element_in: PageElementCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new page element.
    """
    page_element = await element_service.create(db, obj_in=page_element_in, creator_id=current_user.id, updater_id=current_user.id)
    return page_element

@router.get("/{element_id}", response_model=PageElementSchema)
async def read_page_element(
    *,
    db: AsyncSession = Depends(deps.get_db),
    element_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get page element by ID.
    """
    page_element = await element_service.get(db, id=element_id)
    if not page_element:
        raise HTTPException(status_code=404, detail="Page element not found")
    return page_element

@router.put("/{element_id}", response_model=PageElementSchema)
async def update_page_element(
    *,
    db: AsyncSession = Depends(deps.get_db),
    element_id: int,
    page_element_in: PageElementUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update page element.
    """
    page_element = await element_service.get(db, id=element_id)
    if not page_element:
        raise HTTPException(status_code=404, detail="Page element not found")
    
    page_element = await element_service.update(db, db_obj=page_element, obj_in=page_element_in, updater_id=current_user.id)
    return page_element

@router.delete("/{element_id}", response_model=PageElementSchema)
async def delete_page_element(
    *,
    db: AsyncSession = Depends(deps.get_db),
    element_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete page element.
    """
    page_element = await element_service.get(db, id=element_id)
    if not page_element:
        raise HTTPException(status_code=404, detail="Page element not found")
        
    await element_service.remove(db, id=element_id)
    return page_element
