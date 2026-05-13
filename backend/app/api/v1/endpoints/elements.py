from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.user import User
from app.schemas.element import PageElement as PageElementSchema, PageElementCreate, PageElementUpdate
from app.services.element_service import element_service

router = APIRouter()


class SelectorRollbackRequest(BaseModel):
    selector: Optional[str] = None

@router.get("/", response_model=List[PageElementSchema])
async def read_page_elements(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    module_id: int = None,
    page_id: int = None,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve page elements.
    """
    filters = {}
    if module_id:
        filters["module_id"] = module_id
    if page_id:
        filters["page_id"] = page_id
        
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


@router.post("/{element_id}/rollback-selector", response_model=PageElementSchema)
async def rollback_page_element_selector(
    *,
    db: AsyncSession = Depends(deps.get_db),
    element_id: int,
    request: SelectorRollbackRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Roll back current primary selector to a previously recorded selector.
    """
    page_element = await element_service.get(db, id=element_id)
    if not page_element:
        raise HTTPException(status_code=404, detail="Page element not found")

    metadata = dict(page_element.metadata_json or {})
    previous_selectors = [str(s).strip() for s in metadata.get("previous_primary_selectors") or [] if str(s).strip()]
    target_selector = str(request.selector or "").strip() or (previous_selectors[0] if previous_selectors else "")

    if not target_selector:
        raise HTTPException(status_code=400, detail="No previous selector available to roll back")
    if target_selector not in previous_selectors:
        raise HTTPException(status_code=400, detail="Requested selector is not in rollback history")

    current_selector = page_element.locator_value
    remaining_previous = [selector for selector in previous_selectors if selector != target_selector]
    if current_selector and current_selector != target_selector:
        remaining_previous.insert(0, current_selector)

    metadata["previous_primary_selectors"] = _ordered_unique(remaining_previous)[:20]
    human_verified = [target_selector] + list(metadata.get("human_verified_selectors") or [])
    metadata["human_verified_selectors"] = _ordered_unique(human_verified)[:20]

    learning_notes = list(metadata.get("learning_notes") or [])
    learning_notes.insert(
        0,
        f"{datetime.now(timezone.utc).isoformat()} | Rolled back primary selector to: {target_selector}"
    )
    metadata["learning_notes"] = learning_notes[:20]
    metadata["learning_updated_at"] = datetime.now(timezone.utc).isoformat()

    page_element.metadata_json = metadata
    page_element.locator_value = target_selector
    page_element.locator_type = _infer_locator_type(target_selector)
    page_element.updater_id = current_user.id

    page_element = await element_service.update(
        db,
        db_obj=page_element,
        obj_in={
            "locator_value": page_element.locator_value,
            "locator_type": page_element.locator_type,
            "metadata_json": page_element.metadata_json,
        },
        updater_id=current_user.id,
    )
    return page_element


def _ordered_unique(values: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _infer_locator_type(selector: str) -> str:
    text = str(selector or "").strip()
    lower = text.lower()
    if text.startswith("//") or lower.startswith("xpath="):
        return "xpath"
    if lower.startswith("text="):
        return "text"
    if text.startswith("#") or text.startswith(".") or text.startswith("[") or ":" in text:
        return "css"
    return "css"
