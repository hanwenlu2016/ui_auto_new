from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.core.logger import logger
from app.models.user import User
from app.models.element import PageElement
from app.models.page import Page
from app.models.module import Module
from app.models.heal_log import HealLog
from app.models.feedback import StepFeedback
from sqlalchemy.orm import joinedload
from app.services.ai_service import ai_service

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────




# ScenariosRequest and ScenariosResponse removed as /scenarios is no longer used.

class DiscoveryRequest(BaseModel):
    dom_snapshot: str
    model_id: Optional[str] = None

class DiscoveryResponse(BaseModel):
    elements: List[Dict[str, Any]]
    message: str


class GenerateRequest(BaseModel):
    prompt: str
    model_id: Optional[str] = None
    project_id: Optional[int] = None
    business_rules: Optional[str] = None


class GenerateResponse(BaseModel):
    steps: List[Dict[str, Any]]
    message: str


class HealRequest(BaseModel):
    element_id: int
    page_source: str
    screenshot_description: Optional[str] = None
    case_id: Optional[int] = None
    step_index: Optional[int] = None


class HealResponse(BaseModel):
    locator_chain: Dict[str, Any]
    confidence: float
    change_summary: str
    explanation: str
    log_id: Optional[int] = None


class FeedbackRequest(BaseModel):
    project_id: Optional[int] = None
    case_id: Optional[int] = None
    step_index: Optional[int] = None
    feedback_type: str                           # thumbs_up / thumbs_down / correction
    original_step: Optional[Dict[str, Any]] = None
    corrected_step: Optional[Dict[str, Any]] = None
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    message: str


# ─── Endpoints ────────────────────────────────────────────────────────────────




# /scenarios endpoint removed. Use /generate for single path output.

@router.post("/generate", response_model=GenerateResponse)
async def generate_steps(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: GenerateRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Generate a single executable step list from natural language.
    """
    logger.info(f"AI Generate Request | prompt={request.prompt[:80]}")
    project_memory = None
    if request.project_id:
        project_memory = await ai_service.load_project_memory(db, request.project_id)

    steps = await ai_service.generate_steps_from_text(
        db=db,
        prompt=request.prompt,
        business_rules=request.business_rules,
        project_memory=project_memory,
        model_id=request.model_id,
    )
    if project_memory and steps:
        steps = ai_service.bind_steps_to_library(steps, project_memory)
    return {
        "steps": steps,
        "message": f"AI 已生成 {len(steps)} 个步骤。"
    }

@router.post("/discover", response_model=DiscoveryResponse)
async def discover_elements(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: DiscoveryRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    [Module 2 Extension] AI Page Modeling & Element Discovery.
    Analyzes a DOM snapshot and recommends PageElements to save to the library.
    """
    logger.info(f"AI Discovery Request | DOM Size: {len(request.dom_snapshot)}")
    try:
        elements = await ai_service.discover_page_elements(
            db=db,
            dom_snapshot=request.dom_snapshot,
            model_id=request.model_id
        )
        return {
            "elements": elements,
            "message": f"AI 已成功在页面中识别出 {len(elements)} 个关键交互元素。"
        }
    except Exception as e:
        logger.error(f"AI Discovery Failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI Discovery Failed: {str(e)}")


@router.post("/heal", response_model=HealResponse)
async def heal_element(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: HealRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    [Module 3] AI Self-healing: find replacement locator_chain for a broken element.
    Writes a HealLog record for human review.
    """
    # 1. Fetch element metadata
    result = await db.execute(
        select(PageElement).where(PageElement.id == request.element_id)
    )
    element = result.scalar_one_or_none()
    if not element or not element.metadata_json:
        raise HTTPException(status_code=400, detail="Element metadata not found for healing")

    # 2. Call AI
    healing = await ai_service.heal_element(
        db=db,
        element_metadata=element.metadata_json,
        page_source=request.page_source,
        screenshot_description=request.screenshot_description,
        model_id=None,  # Heal endpoint currently doesn't specify model_id, using default
    )

    # 3. Write HealLog
    chain = healing.get("locator_chain", {})
    healed = chain.get("primary") or chain.get("fallback_1")
    log = HealLog(
        case_id=request.case_id,
        element_id=request.element_id,
        step_index=request.step_index,
        original_selector=element.locator_value,
        healed_selector=healed,
        heal_method="ai_locator_chain",
        locator_chain_json=chain,
        confidence=healing.get("confidence", 0.0),
        change_summary=healing.get("change_summary", ""),
        explanation=healing.get("explanation", ""),
        status="auto_healed" if healed else "manual_review",
    )
    db.add(log)
    
    # 4. Write back to Element Library if confidence is high
    from datetime import datetime
    if healing.get("confidence", 0.0) >= 0.8 and healed:
        element.locator_value = healed
        # Ensure metadata_json is a dict before updating
        current_meta = element.metadata_json or {}
        if isinstance(current_meta, str):
            try:
                import json
                current_meta = json.loads(current_meta)
            except:
                current_meta = {}
        element.metadata_json = {
            **current_meta,
            "last_healed_at": datetime.utcnow().isoformat(),
        }
        db.add(element)
        logger.info(f"Auto-healed element {element.id} with new selector: {healed}")

    await db.commit()
    await db.refresh(log)

    return {
        "locator_chain": chain,
        "confidence": healing.get("confidence", 0.0),
        "change_summary": healing.get("change_summary", ""),
        "explanation": healing.get("explanation", ""),
        "log_id": log.id,
    }


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: FeedbackRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    [Module 4] RLHF: record thumbs_up / thumbs_down / correction for a generated step.
    Feedback is later injected as project memory into future prompts.
    """
    # Build a concise AI note for corrections
    ai_notes = None
    if request.feedback_type == "correction" and request.corrected_step:
        orig_target = (request.original_step or {}).get("target", "?")
        new_target = request.corrected_step.get("target", "?")
        if orig_target != new_target:
            ai_notes = f"Selector correction: '{orig_target}' → '{new_target}'"

    fb = StepFeedback(
        project_id=request.project_id,
        case_id=request.case_id,
        step_index=request.step_index,
        feedback_type=request.feedback_type,
        original_step=request.original_step,
        corrected_step=request.corrected_step,
        comment=request.comment,
        ai_notes=ai_notes,
        creator_id=current_user.id,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)

    return {"id": fb.id, "message": f"反馈已记录（{request.feedback_type}），将用于优化项目 AI 记忆。"}


@router.get("/heal-logs")
async def get_heal_logs(
    *,
    db: AsyncSession = Depends(deps.get_db),
    case_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Query HealLog records for human review dashboard.
    """
    query = select(HealLog)
    if case_id:
        query = query.where(HealLog.case_id == case_id)
    if status:
        query = query.where(HealLog.status == status)
    query = query.order_by(HealLog.created_at.desc()).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": l.id,
            "case_id": l.case_id,
            "element_id": l.element_id,
            "step_index": l.step_index,
            "original_selector": l.original_selector,
            "healed_selector": l.healed_selector,
            "confidence": l.confidence,
            "change_summary": l.change_summary,
            "status": l.status,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


@router.get("/feedbacks")
async def get_feedbacks(
    *,
    db: AsyncSession = Depends(deps.get_db),
    project_id: Optional[int] = None,
    feedback_type: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Query StepFeedback records for project memory review.
    """
    query = select(StepFeedback)
    if project_id:
        query = query.where(StepFeedback.project_id == project_id)
    if feedback_type:
        query = query.where(StepFeedback.feedback_type == feedback_type)
    query = query.order_by(StepFeedback.created_at.desc()).limit(limit)
    result = await db.execute(query)
    feedbacks = result.scalars().all()

    return [
        {
            "id": f.id,
            "project_id": f.project_id,
            "case_id": f.case_id,
            "feedback_type": f.feedback_type,
            "comment": f.comment,
            "ai_notes": f.ai_notes,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in feedbacks
    ]


# ─── Private Helpers ──────────────────────────────────────────────────────────

# Helpers moved to ai_service.py for reusability with agent_service.py
