from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import json
import re
from uuid import uuid4
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
    quality: Optional[Dict[str, Any]] = None


# ScenariosRequest and ScenariosResponse removed as /scenarios is no longer used.

class DiscoveryRequest(BaseModel):
    dom_snapshot: str
    model_id: Optional[str] = None

class DiscoveryResponse(BaseModel):
    elements: List[Dict[str, Any]]
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
    Now bridged with Page-Agent library for stable selector reuse.
    """
    project_memory = None
    if request.project_id:
        project_memory = await _load_project_memory(db, request.project_id)

    logger.info(f"AI Generate Request: {request.prompt[:100]}...")
    try:
        result = await ai_service.generate_steps_bundle_from_text(
            db=db,
            prompt=request.prompt,
            dom_snapshot=request.dom_snapshot,
            screenshot_description=request.screenshot_description,
            business_rules=request.business_rules,
            project_memory=project_memory,
            model_id=request.model_id,
        )
        steps = result.get("steps") or []
        trace = result.get("trace") or {"trace_id": uuid4().hex[:12]}

        # ─── New: Page-Agent Binding ──────────────────────────────────────────
        if project_memory and steps:
            steps = _bind_steps_to_library(steps, project_memory)
        # ──────────────────────────────────────────────────────────────────────

        msg = (
            f"已为您规划 {len(steps)} 个自动化步骤，每步包含多重定位备用选择器。"
            if steps else
            "未能识别出具体操作，请尝试更明确的描述，例如：「打开百度，输入 Python 并点击搜索」。"
        )
        # Add a hint if elements were matched
        matched_count = sum(1 for s in steps if s.get("element_id"))
        quality = _build_generation_quality_summary(steps, trace, matched_count)
        if matched_count > 0:
            msg += f" (已成功匹配 {matched_count} 个项目元素)"

        logger.info(
            "AI_GENERATE_QUALITY %s",
            json.dumps(
                {
                    **quality,
                    "prompt_preview": request.prompt[:200],
                    "project_id": request.project_id,
                    "model_id": request.model_id,
                    "raw_response_preview": trace.get("raw_response_preview", ""),
                },
                ensure_ascii=False,
            ),
        )
        logger.info(f"AI Generate Success: {len(steps)} steps | Matched: {matched_count} | Trace: {quality['trace_id']}")
        return {"steps": steps, "message": msg, "quality": quality}
    except Exception as e:
        logger.error(f"AI Generate Failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI Step Generation Failed: {str(e)}")


# /scenarios endpoint removed. Use /generate for single path output.

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

    if healed:
        element.metadata_json = _merge_element_learning_metadata(
            metadata=element.metadata_json,
            selectors=_selectors_from_chain(chain),
            locator_chain=chain,
            bucket="healing_selectors",
            note=f"AI heal suggested selector: {healed}",
        )
        db.add(element)

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

    if request.feedback_type == "correction":
        await _apply_feedback_learning(
            db=db,
            original_step=request.original_step,
            corrected_step=request.corrected_step,
            comment=request.comment,
        )

    await db.commit()
    await db.refresh(fb)

    return {"id": fb.id, "message": f"反馈已记录（{request.feedback_type}），将用于优化项目 AI 记忆。"}


@router.get("/heal-logs")
async def get_heal_logs(
    *,
    db: AsyncSession = Depends(deps.get_db),
    project_id: Optional[int] = None,
    page_id: Optional[int] = None,
    case_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Query HealLog records for human review dashboard.
    """
    query = (
        select(HealLog, PageElement, Page)
        .outerjoin(PageElement, HealLog.element_id == PageElement.id)
        .outerjoin(Page, Page.id == PageElement.page_id)
    )
    if project_id:
        query = query.outerjoin(Module, Module.id == Page.module_id).where(Module.project_id == project_id)
    if page_id:
        query = query.where(Page.id == page_id)
    if case_id:
        query = query.where(HealLog.case_id == case_id)
    if status:
        query = query.where(HealLog.status == status)
    query = query.order_by(HealLog.created_at.desc()).limit(limit)
    result = await db.execute(query)
    logs = result.all()

    return [
        {
            "id": l.id,
            "case_id": l.case_id,
            "element_id": l.element_id,
            "element_name": element.name if element else None,
            "page_id": page.id if page else None,
            "page_name": page.name if page else None,
            "step_index": l.step_index,
            "original_selector": l.original_selector,
            "healed_selector": l.healed_selector,
            "candidate_selector": _best_memory_selector(l),
            "confidence": l.confidence,
            "change_summary": l.change_summary,
            "explanation": l.explanation,
            "status": l.status,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l, element, page in logs
    ]


@router.post("/heal-logs/{log_id}/promote")
async def promote_heal_log(
    *,
    db: AsyncSession = Depends(deps.get_db),
    log_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """将自愈建议提升为元素主选择器。"""
    result = await db.execute(
        select(HealLog, PageElement)
        .join(PageElement, HealLog.element_id == PageElement.id)
        .where(HealLog.id == log_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Heal log not found")

    log, element = row
    candidate_selector = _best_memory_selector(log)
    if not candidate_selector:
        raise HTTPException(status_code=400, detail="No promotable selector found")

    previous_selector = element.locator_value
    element.locator_value = candidate_selector
    element.locator_type = _infer_locator_type(candidate_selector)
    element.updater_id = current_user.id
    element.metadata_json = _merge_element_learning_metadata(
        metadata=element.metadata_json,
        selectors=[candidate_selector, previous_selector],
        locator_chain=log.locator_chain_json if isinstance(log.locator_chain_json, dict) else None,
        bucket="human_verified_selectors",
        note=f"Promoted heal log #{log.id} selector: {candidate_selector}",
    )
    if previous_selector and previous_selector != candidate_selector:
        previous_selectors = list((element.metadata_json or {}).get("previous_primary_selectors") or [])
        previous_selectors.insert(0, previous_selector)
        element.metadata_json["previous_primary_selectors"] = _ordered_unique(previous_selectors)[:20]

    log.status = "promoted"
    log.healed_selector = candidate_selector
    db.add(element)
    db.add(log)
    await db.commit()

    return {
        "message": "自愈建议已提升为主选择器",
        "element_id": element.id,
        "locator_value": element.locator_value,
        "locator_type": element.locator_type,
        "log_id": log.id,
        "status": log.status,
    }


@router.post("/heal-logs/{log_id}/reject")
async def reject_heal_log(
    *,
    db: AsyncSession = Depends(deps.get_db),
    log_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """驳回一条自愈建议，保留记录但不提升。"""
    del current_user
    result = await db.execute(select(HealLog).where(HealLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Heal log not found")

    log.status = "rejected"
    db.add(log)
    await db.commit()
    return {"message": "已驳回该自愈建议", "log_id": log.id, "status": log.status}


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

def _bind_steps_to_library(steps: List[Dict[str, Any]], project_memory: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Match AI-generated steps to the project's Page Object Library.
    Prefer exact selector matches, then fall back to semantic scoring.
    """
    library = project_memory.get("page_object_library", [])
    if not library:
        return steps

    flat_elements: List[Dict[str, Any]] = []
    for page in library:
        p_id = page.get("page_id")
        p_name = page.get("page_name")
        for el in page.get("elements", []):
            selectors = _collect_step_candidate_selectors({
                "target": el.get("selector"),
                "selector": el.get("selector"),
                "locator_chain": {
                    "primary": el.get("selector"),
                    "fallback_1": (el.get("selectors") or [None, None])[1] if len(el.get("selectors") or []) > 1 else None,
                    "fallback_2": (el.get("selectors") or [None, None, None])[2] if len(el.get("selectors") or []) > 2 else None,
                    "fallback_3": (el.get("selectors") or [None, None, None, None])[3] if len(el.get("selectors") or []) > 3 else None,
                }
            })
            flat_elements.append({
                **el,
                "page_id": p_id,
                "page_name": p_name,
                "selectors": selectors or _ordered_unique(el.get("selectors") or [el.get("selector")]),
            })

    matched_steps = []
    for step in steps:
        matched = _find_best_library_element(step, flat_elements)
        if matched:
            official_selector = str(matched.get("selector") or "").strip()
            step["element_id"] = matched.get("element_id")
            step["page_id"] = matched.get("page_id")
            if official_selector:
                step["target"] = official_selector
                step["selector"] = official_selector
                locator_chain = step.get("locator_chain")
                if not isinstance(locator_chain, dict) or not str(locator_chain.get("primary") or "").strip():
                    step["locator_chain"] = {"primary": official_selector}
        matched_steps.append(step)

    return matched_steps


async def _load_project_memory(db: AsyncSession, project_id: int) -> Dict[str, Any]:
    """
    Load project-specific context:
    1. Feedback history (RLHF)
    2. Page Object Library (Pages & Elements) for Page-Agent framework
    """
    # 1. Load feedbacks
    fb_result = await db.execute(
        select(StepFeedback)
        .where(StepFeedback.project_id == project_id)
        .where(StepFeedback.feedback_type.in_(["thumbs_up", "correction"]))
        .order_by(StepFeedback.created_at.desc())
        .limit(20)
    )
    feedbacks = fb_result.scalars().all()

    heal_result = await db.execute(
        select(HealLog, PageElement, Page)
        .join(PageElement, HealLog.element_id == PageElement.id)
        .join(Page, Page.id == PageElement.page_id)
        .join(Module, Module.id == Page.module_id)
        .where(Module.project_id == project_id)
        .where(HealLog.status == "auto_healed")
        .order_by(HealLog.created_at.desc())
        .limit(20)
    )
    heal_rows = heal_result.all()
    
    # 2. Load Page Object Library
    # Pages belong to Modules, which belong to Projects
    page_query = (
        select(Page)
        .join(Module)
        .where(Module.project_id == project_id)
        .options(joinedload(Page.page_elements))
    )
    page_result = await db.execute(page_query)
    pages = page_result.unique().scalars().all()
    
    page_object_library = []
    for p in pages:
        elements = [
            {
                "element_id": e.id,
                "name": e.name,
                "selector": e.locator_value,
                "selectors": _collect_element_selectors(e.locator_value, e.metadata_json),
                "type": e.locator_type,
                "description": e.description
            }
            for e in p.page_elements
        ]
        if elements:
            page_object_library.append({
                "page_id": p.id,
                "page_name": p.name,
                "elements": elements
            })

    return {
        "feedbacks": [
            {
                "feedback_type": f.feedback_type,
                "ai_notes": f.ai_notes,
                "comment": f.comment,
            }
            for f in feedbacks
        ],
        "page_object_library": page_object_library,
        "healing_memories": [
            {
                "page_name": page.name,
                "element_name": element.name,
                "original_selector": log.original_selector,
                "healed_selector": _best_memory_selector(log),
                "change_summary": log.change_summary,
                "confidence": log.confidence,
            }
            for log, element, page in heal_rows
            if _best_memory_selector(log)
        ]
    }


def _extract_step_selector(step: Optional[Dict[str, Any]]) -> Optional[str]:
    if not step:
        return None
    for key in ("target", "selector"):
        value = str(step.get(key) or "").strip()
        if value:
            return value
    return None


def _ordered_unique(values: List[Optional[str]]) -> List[str]:
    seen = set()
    result: List[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _selectors_from_chain(locator_chain: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(locator_chain, dict):
        return []
    return _ordered_unique([
        locator_chain.get("primary"),
        locator_chain.get("fallback_1"),
        locator_chain.get("fallback_2"),
        locator_chain.get("fallback_3"),
    ])


def _collect_element_selectors(primary_selector: Optional[str], metadata_json: Optional[Dict[str, Any]]) -> List[str]:
    metadata = metadata_json or {}
    return _ordered_unique(
        list(metadata.get("human_verified_selectors") or [])
        + [metadata.get("last_healed_selector")]
        + _selectors_from_chain(metadata.get("ai_recommended_locator_chain"))
        + list(metadata.get("healing_selectors") or [])
        + [primary_selector]
    )


def _normalize_selector(selector: Optional[str]) -> str:
    return re.sub(r"\s+", " ", str(selector or "").replace(":visible", "").strip())


def _normalize_match_text(text: Optional[str]) -> str:
    normalized = str(text or "").strip().lower()
    normalized = re.sub(r"[\[\](){}<>\"'`]+", " ", normalized)
    normalized = re.sub(r"[_:/\\|,+.=*-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _compact_match_text(text: Optional[str]) -> str:
    return re.sub(r"[\W_]+", "", _normalize_match_text(text), flags=re.UNICODE)


def _tokenize_match_text(text: Optional[str]) -> List[str]:
    return [token for token in re.split(r"\s+", _normalize_match_text(text)) if len(token) >= 2]


def _collect_step_candidate_selectors(step: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(step, dict):
        return []
    selectors = [
        step.get("target"),
        step.get("selector"),
    ]
    locator_chain = step.get("locator_chain")
    if isinstance(locator_chain, dict):
        selectors.extend([
            locator_chain.get("primary"),
            locator_chain.get("fallback_1"),
            locator_chain.get("fallback_2"),
            locator_chain.get("fallback_3"),
        ])
    return _ordered_unique([_normalize_selector(selector) for selector in selectors if _normalize_selector(selector)])


def _build_element_aliases(element: Dict[str, Any]) -> List[str]:
    aliases = [
        element.get("name"),
        element.get("description"),
        element.get("page_name"),
        f"{element.get('page_name', '')} {element.get('name', '')}",
        f"{element.get('page_name', '')} {element.get('description', '')}",
    ]
    return _ordered_unique([_normalize_match_text(alias) for alias in aliases if _normalize_match_text(alias)])


def _score_library_element_match(step: Dict[str, Any], element: Dict[str, Any]) -> int:
    step_selectors = set(_collect_step_candidate_selectors(step))
    element_selectors = {_normalize_selector(selector) for selector in element.get("selectors") or [] if _normalize_selector(selector)}
    if step_selectors and element_selectors:
        exact_overlap = step_selectors & element_selectors
        if exact_overlap:
            return 120

    target_text = str(step.get("target") or "").strip()
    description = str(step.get("description") or "").strip()
    value = str(step.get("value") or "").strip()
    step_text = " ".join([target_text, description, value])
    normalized_step_text = _normalize_match_text(step_text)
    compact_step_text = _compact_match_text(step_text)
    step_tokens = set(_tokenize_match_text(step_text))
    action = str(step.get("action") or "").strip().lower()

    score = 0
    for alias in _build_element_aliases(element):
        if not alias:
            continue
        compact_alias = _compact_match_text(alias)
        alias_tokens = set(_tokenize_match_text(alias))
        if normalized_step_text == alias:
            score = max(score, 95)
        elif compact_alias and compact_alias == compact_step_text:
            score = max(score, 92)
        elif compact_alias and compact_alias in compact_step_text:
            score = max(score, 84)
        elif compact_step_text and compact_step_text in compact_alias:
            score = max(score, 78)

        overlap = len(step_tokens & alias_tokens)
        if overlap:
            score = max(score, 55 + overlap * 8)

    if action in {"fill", "select"}:
        element_type = str(element.get("type") or "").lower()
        if element_type in {"input", "select", "textarea"}:
            score += 6
    if action in {"click", "hover", "press"}:
        element_type = str(element.get("type") or "").lower()
        if element_type in {"button", "link", "other"}:
            score += 4

    return score


def _find_best_library_element(step: Dict[str, Any], elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best_match: Optional[Dict[str, Any]] = None
    best_score = 0
    for element in elements:
        score = _score_library_element_match(step, element)
        if score > best_score:
            best_match = element
            best_score = score
    if best_score >= 70:
        return best_match
    return None


def _build_generation_quality_summary(
    steps: List[Dict[str, Any]],
    trace: Dict[str, Any],
    matched_count: int,
) -> Dict[str, Any]:
    interactive_actions = {"click", "fill", "select", "hover", "press", "wait_for_selector"}
    interactive_count = sum(
        1 for step in steps if str(step.get("action") or "") in interactive_actions
    )
    unbound_interactive_count = sum(
        1
        for step in steps
        if str(step.get("action") or "") in interactive_actions and not step.get("element_id")
    )
    bind_rate = round((matched_count / interactive_count), 4) if interactive_count else 1.0
    return {
        "trace_id": trace.get("trace_id"),
        "model_name": trace.get("model_name"),
        "parse_source": trace.get("parse_source"),
        "fallback_used": bool(trace.get("fallback_used")),
        "fallback_reason": trace.get("fallback_reason"),
        "raw_response_length": trace.get("raw_response_length", 0),
        "parsed_step_count": trace.get("parsed_step_count", 0),
        "cleaned_step_count": trace.get("cleaned_step_count", 0),
        "final_step_count": len(steps),
        "interactive_step_count": interactive_count,
        "assertion_step_count": trace.get("assertion_step_count", 0),
        "ai_auto_count": trace.get("ai_auto_count", 0),
        "auto_assert_added": bool(trace.get("auto_assert_added")),
        "matched_count": matched_count,
        "unbound_interactive_count": unbound_interactive_count,
        "bind_rate": bind_rate,
    }


def _merge_element_learning_metadata(
    *,
    metadata: Optional[Dict[str, Any]],
    selectors: List[str],
    locator_chain: Optional[Dict[str, Any]],
    bucket: str,
    note: Optional[str],
) -> Dict[str, Any]:
    next_metadata = dict(metadata or {})
    merged_selectors = _ordered_unique(selectors + list(next_metadata.get(bucket) or []))
    if merged_selectors:
        next_metadata[bucket] = merged_selectors[:12]
        next_metadata["last_healed_selector"] = merged_selectors[0]
    if locator_chain:
        next_metadata["ai_recommended_locator_chain"] = locator_chain

    learning_notes = list(next_metadata.get("learning_notes") or [])
    if note:
        timestamp = datetime.now(timezone.utc).isoformat()
        learning_notes.insert(0, f"{timestamp} | {note}")
        next_metadata["learning_notes"] = learning_notes[:20]

    next_metadata["learning_updated_at"] = datetime.now(timezone.utc).isoformat()
    return next_metadata


async def _apply_feedback_learning(
    *,
    db: AsyncSession,
    original_step: Optional[Dict[str, Any]],
    corrected_step: Optional[Dict[str, Any]],
    comment: Optional[str],
) -> None:
    element_id = (corrected_step or {}).get("element_id") or (original_step or {}).get("element_id")
    if not element_id:
        return

    corrected_selector = _extract_step_selector(corrected_step)
    if not corrected_selector:
        return

    result = await db.execute(select(PageElement).where(PageElement.id == element_id))
    element = result.scalar_one_or_none()
    if not element:
        return

    selectors = [corrected_selector] + _selectors_from_chain((corrected_step or {}).get("locator_chain"))
    note = f"Human correction verified selector: {corrected_selector}"
    if comment:
        note += f" | {comment}"

    element.metadata_json = _merge_element_learning_metadata(
        metadata=element.metadata_json,
        selectors=selectors,
        locator_chain=(corrected_step or {}).get("locator_chain"),
        bucket="human_verified_selectors",
        note=note,
    )
    db.add(element)


def _best_memory_selector(log: HealLog) -> Optional[str]:
    selectors = _selectors_from_chain(log.locator_chain_json if isinstance(log.locator_chain_json, dict) else {})
    if selectors:
        return selectors[0]
    healed_selector = str(log.healed_selector or "").strip()
    if healed_selector and healed_selector != "PageAgent_AI":
        return healed_selector
    return None


def _infer_locator_type(selector: str) -> str:
    text = str(selector or "").strip()
    lower = text.lower()
    if text.startswith("//") or lower.startswith("xpath="):
        return "xpath"
    if lower.startswith("text="):
        return "text"
    if text.startswith("#"):
        return "css"
    if lower.startswith("[") or text.startswith(".") or ":" in text:
        return "css"
    return "css"
