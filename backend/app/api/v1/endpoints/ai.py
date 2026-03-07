from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.core.logger import logger
from app.models.user import User
from app.models.element import PageElement
from app.models.heal_log import HealLog
from app.models.feedback import StepFeedback
from app.services.ai_service import ai_service

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    dom_snapshot: Optional[str] = None            # 页面 DOM 快照（Top 200 行）
    screenshot_description: Optional[str] = None  # 截图的语义描述
    business_rules: Optional[str] = None          # 业务规则上下文
    project_id: Optional[int] = None              # 用于加载项目记忆
    model_id: Optional[str] = None                # 模型 ID (如 deepseek-chat, minimax-m2.5)


class GenerateResponse(BaseModel):
    steps: List[Dict[str, Any]]
    message: str


class ScenariosRequest(BaseModel):
    prompt: str
    dom_snapshot: Optional[str] = None
    project_id: Optional[int] = None
    model_id: Optional[str] = None


class ScenariosResponse(BaseModel):
    happy_path: List[Dict[str, Any]]
    boundary: List[Dict[str, Any]]
    negative: List[Dict[str, Any]]
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

@router.post("/generate", response_model=GenerateResponse)
async def generate_steps(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: GenerateRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    [Module 1] Generate test steps from natural language + optional multimodal context.
    Supports DOM snapshot and screenshot description injection for richer AI reasoning.
    """
    project_memory = None
    if request.project_id:
        project_memory = await _load_project_memory(db, request.project_id)

    logger.info(f"AI Generate Request: {request.prompt[:100]}...")
    try:
        steps = await ai_service.generate_steps_from_text(
            db=db,
            prompt=request.prompt,
            dom_snapshot=request.dom_snapshot,
            screenshot_description=request.screenshot_description,
            business_rules=request.business_rules,
            project_memory=project_memory,
            model_id=request.model_id,
        )

        msg = (
            f"已为您规划 {len(steps)} 个自动化步骤，每步包含多重定位备用选择器。"
            if steps else
            "未能识别出具体操作，请尝试更明确的描述，例如：「打开百度，输入 Python 并点击搜索」。"
        )
        logger.info(f"AI Generate Success: {len(steps)} steps")
        return {"steps": steps, "message": msg}
    except Exception as e:
        logger.error(f"AI Generate Failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI Step Generation Failed: {str(e)}")


@router.post("/scenarios", response_model=ScenariosResponse)
async def generate_scenarios(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: ScenariosRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    [Module 2] Generate happy_path, boundary, and negative test scenarios in one shot.
    Ideal for comprehensive test coverage from a single feature description.
    """
    project_memory = None
    if request.project_id:
        project_memory = await _load_project_memory(db, request.project_id)

    logger.info(f"AI Scenarios Request: {request.prompt[:100]}...")
    try:
        result = await ai_service.generate_scenarios(
            db=db,
            prompt=request.prompt,
            dom_snapshot=request.dom_snapshot,
            project_memory=project_memory,
            model_id=request.model_id,
        )

        if not result:
            logger.error("AI Scenarios returned None or empty result")
            raise ValueError("AI Service returned invalid empty result")

        h_path = result.get("happy_path") or []
        b_path = result.get("boundary") or []
        n_path = result.get("negative") or []

        total = len(h_path) + len(b_path) + len(n_path)
        logger.info(f"AI Scenarios Success: {total} steps generated")
        
        return {
            "happy_path": h_path,
            "boundary": b_path,
            "negative": n_path,
            "message": f"已生成 {total} 个覆盖三类场景的测试步骤（正向/边界/负面）。",
        }
    except Exception as e:
        logger.error(f"AI Scenarios Failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI Scenario Planning Failed: {str(e)}")


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

async def _load_project_memory(db: AsyncSession, project_id: int) -> Dict[str, Any]:
    """
    Load project-specific feedback history to inject as AI memory context.
    Returns the last 20 corrections and thumbs_up entries.
    """
    result = await db.execute(
        select(StepFeedback)
        .where(StepFeedback.project_id == project_id)
        .where(StepFeedback.feedback_type.in_(["thumbs_up", "correction"]))
        .order_by(StepFeedback.created_at.desc())
        .limit(20)
    )
    feedbacks = result.scalars().all()
    return {
        "feedbacks": [
            {
                "feedback_type": f.feedback_type,
                "ai_notes": f.ai_notes,
                "comment": f.comment,
            }
            for f in feedbacks
        ]
    }
