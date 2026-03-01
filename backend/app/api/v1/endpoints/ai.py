from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from app.api import deps
from app.models.user import User
from app.models.element import PageElement
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ai_service import ai_service

router = APIRouter()

class GenerateRequest(BaseModel):
    prompt: str

class GenerateResponse(BaseModel):
    steps: List[Dict[str, Any]]
    message: str

@router.post("/generate", response_model=GenerateResponse)
async def generate_steps(
    *,
    request: GenerateRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Generate test steps from natural language prompt.
    """
    # Potential place to inject project context from DB
    steps = await ai_service.generate_steps_from_text(request.prompt)
    
    msg = "我已经为您规划好了自动化操作步骤：" if steps else "我是您的自动化助手。我没能从您的指令中识别出具体的网页操作动作，您可以尝试说“打开百度”或“登录流程”。"
    return {"steps": steps, "message": msg}

class HealRequest(BaseModel):
    element_id: int
    page_source: str
    screenshot_base64: Optional[str] = None

class HealResponse(BaseModel):
    new_selector: str
    confidence: float
    explanation: str

@router.post("/heal", response_model=HealResponse)
async def heal_element(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: HealRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    AI Self-healing: Find a replacement selector for a broken element.
    """
    # 1. Fetch element metadata
    from sqlalchemy import select
    result = await db.execute(select(PageElement).where(PageElement.id == request.element_id))
    element = result.scalar_one_or_none()
    
    if not element or not element.metadata_json:
        raise HTTPException(status_code=400, detail="Element metadata not found for healing")
    
    # 2. Call AI service to heal
    healing_result = await ai_service.heal_element(
        element_metadata=element.metadata_json,
        page_source=request.page_source,
        screenshot=request.screenshot_base64
    )
    
    return healing_result
