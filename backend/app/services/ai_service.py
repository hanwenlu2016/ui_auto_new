import os
from typing import List, Dict, Any, Optional
import json
import re
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.core.config import settings
from app.core.logger import logger
from app.models.user import User
from app.models.element import PageElement
from app.models.page import Page
from app.models.module import Module
from app.models.heal_log import HealLog
from app.models.feedback import StepFeedback


# ─── Prompt Templates ─────────────────────────────────────────────────────────

DISCOVERY_SYSTEM_PROMPT = """
You are a UI Modeling Expert. Your task is to analyze a DOM snapshot and identify key interactive elements for test automation.

Focus on:
1. Buttons, Inputs, Selects, Links, and key clickable containers.
2. Form fields and their associated labels.
3. Navigation elements.

For each element, provide:
- name: A clear, semantic name in English or Chinese (e.g. "LoginButton", "用户名输入框")
- locator_type: One of [xpath, css, id, name]
- locator_value: The most stable and unique selector possible.
- type: The element type (button, input, select, link, text, other)
- description: A brief explanation of what the element does.

OUTPUT FORMAT (strict JSON array of objects, no markdown):
[
  {
    "name": "...",
    "locator_type": "...",
    "locator_value": "...",
    "type": "...",
    "description": "..."
  }
]
"""

HEAL_SYSTEM_PROMPT = """
You are a Senior Automation Architect and DOM Forensics Expert.
Mission: Find the SAME logical element in the current DOM (Healing) OR generate the most STABLE selectors for a newly captured element (Recording Reinforcement).

Given: (1) element metadata, (2) current page HTML, (3) optional context/screenshot description.

Goals:
- Prioritize stable attributes: data-testid, aria-label, name, then unique text, then semantic structure.
- Avoid volatile attributes: auto-generated IDs, dynamic classes, absolute XPaths.
- Provide a robust 'locator_chain' with primary and fallbacks.

Return ONLY this JSON:
{
  "locator_chain": {
    "primary": "[data-testid='xxx']",
    "fallback_1": "[aria-label='xxx']",
    "fallback_2": "//relative/xpath",
    "fallback_3": "text='visible_text'",
    "fallback_image": null
  },
  "confidence": 0.95,
  "change_summary": "Description of why these selectors were chosen.",
  "explanation": "Technical reasoning for stability."
}
"""


class AIService:
    """
    Enhanced AI Service — v4.0 (Database-Driven)
    Powers 4 core capabilities across any OpenAI-compatible provider.
    """

    def __init__(self):
        # Stores (AsyncOpenAI client, config_fingerprint) keyed by model DB id.
        # The fingerprint is a hash of api_key + base_url + model_identifier;
        # if any of these change in the DB, the cached client is invalidated and recreated.
        self._clients: Dict[int, tuple[AsyncOpenAI, str]] = {}
        logger.info("Universal AI Service v4.0 initialized (DB-Driven)")


    async def _get_client_from_db(
        self, db: AsyncSession, model_id: Optional[str] = None
    ) -> tuple[Optional[AsyncOpenAI], Optional[str]]:
        """
        Fetch model config from DB and return (client, model_identifier).
        """
        from app.services.ai_model_service import ai_model_service
        
        db_model = None
        if model_id and str(model_id).isdigit():
            db_model = await ai_model_service.get(db, int(model_id))
        
        if not db_model:
            db_model = await ai_model_service.get_default(db)
            
        if not db_model or not db_model.is_active:
            logger.warning("No active AI model found in database.")
            return None, None

        # Cache clients by model ID, but invalidate when config changes.
        # Using a fingerprint of the key fields prevents stale clients after API key rotation.
        fingerprint = f"{db_model.api_key}:{db_model.base_url}:{db_model.model_identifier}"
        cached = self._clients.get(db_model.id)
        if cached is None or cached[1] != fingerprint:
            try:
                client = AsyncOpenAI(
                    api_key=db_model.api_key,
                    base_url=db_model.base_url,
                    timeout=120.0
                )
                self._clients[db_model.id] = (client, fingerprint)
                if cached is not None:
                    logger.info(f"AI client refreshed for model '{db_model.name}' (config changed)")
            except Exception as e:
                logger.error(f"Failed to init AI client for {db_model.name}: {e}")
                return None, None
                
        return self._clients[db_model.id][0], db_model.model_identifier

    async def chat_completion(
        self,
        db: AsyncSession,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generic chat completion wrapper for internal use (e.g. PageAgent proxy).
        """
        client, model_name = await self._get_client_from_db(db, model_id)
        
        if not client:
            return {"content": "Error: No active AI model configured."}

        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
            )
            return {"content": response.choices[0].message.content}
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            return {"content": f"Error: {str(e)}"}



    # ─── Module 2: Page Modeling & Element Discovery ─────────────────────────

    async def discover_page_elements(
        self,
        db: AsyncSession,
        dom_snapshot: str,
        model_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        [Module 2] Analyze DOM and return suggested PageElements.
        """
        client, model_name = await self._get_client_from_db(db, model_id)
        if not client:
            return []

        # Keep snapshot size reasonable (approx 100k chars)
        snapshot = dom_snapshot[:100000]
        
        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": DISCOVERY_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Please analyze this DOM and discover key interactive elements:\n\n{snapshot}"},
                ],
                temperature=0.1,
            )
            raw = response.choices[0].message.content
            elements = self._parse_json_array(raw) or []
            return elements
        except Exception as e:
            logger.error(f"discover_page_elements failed: {e}")
            return []

    # generate_scenarios removed. Simplified to single path in generate_steps_from_text.

    # ─── Module 3: Self-Healing with Locator Chain ───────────────────────────

    async def heal_element(
        self,
        db: AsyncSession,
        element_metadata: Dict[str, Any],
        page_source: str,
        screenshot_description: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        AI-powered element healing using DB-configured model.
        """
        client, model_name = await self._get_client_from_db(db, model_id)

        if not client:
            text = element_metadata.get("innerText", "")
            return {
                "locator_chain": {
                    "primary": f"text={text}",
                    "fallback_1": None, "fallback_2": None,
                    "fallback_3": None, "fallback_image": None,
                },
                "confidence": 0.2,
                "change_summary": "AI unavailable — text match fallback.",
                "explanation": "No active AI model.",
            }

        # Truncate DOM for context window
        truncated_source = page_source[:25000]
        input_data = (
            f"ORIGINAL ELEMENT METADATA:\n{json.dumps(element_metadata, indent=2, ensure_ascii=False)}\n\n"
            f"CURRENT PAGE HTML (TRUNCATED):\n{truncated_source}"
        )
        if screenshot_description:
            input_data += f"\n\nSCREENSHOT DESCRIPTION:\n{screenshot_description}"

        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": HEAL_SYSTEM_PROMPT},
                    {"role": "user", "content": input_data},
                ],
                temperature=0.05,
            )
            raw = response.choices[0].message.content
            result = self._parse_json_object(raw)
            if result and "locator_chain" in result:
                return result
            raise ValueError("Missing locator_chain in response")
        except Exception as e:
            logger.error(f"heal_element failed ({model_name}): {e}")
            text = element_metadata.get("innerText", "")
            aria = element_metadata.get("ariaLabel", "")
            return {
                "locator_chain": {
                    "primary": f"[aria-label='{aria}']" if aria else f"text={text}",
                    "fallback_1": f"text={text}" if text else None,
                    "fallback_2": None, "fallback_3": None, "fallback_image": None,
                },
                "confidence": 0.3,
                "change_summary": f"AI error: {str(e)[:200]}",
                "explanation": "Fallback to metadata-based text/aria match.",
            }

    # ─── Helpers ─────────────────────────────────────────────────────────────

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _parse_json_array(self, text: str) -> Optional[List[Dict[str, Any]]]:
        try:
            # Look for [ ... ]
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
            return None
        except:
            return None

    def _parse_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            # Look for { ... }
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
            return None
        except:
            return None

    def _normalize_selector(self, selector: Any) -> str:
        return re.sub(r":visible\b", "", str(selector or "").strip(), flags=re.IGNORECASE)

    def _get_step_selector_candidates(self, step: Dict[str, Any]) -> List[str]:
        candidates: List[str] = []

        for raw in [step.get("target"), step.get("selector")]:
            normalized = self._normalize_selector(raw)
            if normalized:
                candidates.append(normalized)

        locator_chain = step.get("locator_chain")
        if isinstance(locator_chain, dict):
            for raw in [
                locator_chain.get("primary"),
                locator_chain.get("fallback_1"),
                locator_chain.get("fallback_2"),
                locator_chain.get("fallback_3"),
            ]:
                normalized = self._normalize_selector(raw)
                if normalized:
                    candidates.append(normalized)
        elif isinstance(locator_chain, list):
            for raw in locator_chain:
                normalized = self._normalize_selector(raw)
                if normalized:
                    candidates.append(normalized)

        return list(dict.fromkeys(candidates))

    def bind_steps_to_library(self, steps: List[Dict[str, Any]], project_memory: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Match AI-generated steps to the project's Page Object Library.
        Matches by name (case-insensitive) or by selector.
        """
        library = project_memory.get("page_object_library", [])
        if not library:
            return steps

        name_map = {}
        selector_map = {}
        
        for page in library:
            p_id = page.get("page_id")
            p_name = page.get("page_name")
            for el in page.get("elements", []):
                el_id = el.get("element_id")
                e_name = el.get("name", "").lower().strip()
                if e_name:
                    name_map[e_name] = (el_id, p_id, el.get("selector"))
                e_sel = self._normalize_selector(el.get("selector"))
                if e_sel:
                    selector_map[e_sel] = (el_id, p_id, el.get("selector"))

        matched_steps = []
        for step in steps:
            target = (step.get("target") or step.get("selector") or "").strip()
            desc = step.get("description", "").lower()
            
            found_el_id = None
            found_page_id = None
            found_selector = None
            
            for candidate in self._get_step_selector_candidates(step):
                if candidate in selector_map:
                    found_el_id, found_page_id, found_selector = selector_map[candidate]
                    break
            
            if not found_el_id:
                for name, (el_id, p_id, sel) in name_map.items():
                    if target.lower() == name or name in desc:
                        found_el_id = el_id
                        found_page_id = p_id
                        found_selector = sel
                        if target.lower() == name:
                            step["target"] = sel
                            step["selector"] = sel
                        break
            
            if found_el_id:
                step["element_id"] = found_el_id
                step["page_id"] = found_page_id
                if found_selector:
                    step["target"] = found_selector
                    step["selector"] = found_selector
                
            matched_steps.append(step)
        
        return matched_steps

    async def load_project_memory(self, db: AsyncSession, project_id: int) -> Dict[str, Any]:
        """
        Load project-specific context:
        1. Feedback history (RLHF)
        2. Page Object Library (Pages & Elements) for Page-Agent framework
        """
        fb_result = await db.execute(
            select(StepFeedback)
            .where(StepFeedback.project_id == project_id)
            .where(StepFeedback.feedback_type.in_(["thumbs_up", "correction"]))
            .order_by(StepFeedback.created_at.desc())
            .limit(20)
        )
        feedbacks = fb_result.scalars().all()
        
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
            "page_object_library": page_object_library
        }




ai_service = AIService()
