import os
from typing import List, Dict, Any, Optional
import json
import re
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logger import logger


# ─── Prompt Templates ─────────────────────────────────────────────────────────

SUPER_PROMPT_SYSTEM = """
You are an elite UI Test Automation Engineer with 10+ years of experience.
Your mission: convert user instructions into robust, production-grade Playwright test steps.

You MUST:
1. Prefer stable selectors in this priority order:
   [data-testid] > [aria-label] > relative XPath > text= > CSS class

2. For EVERY interactive step, provide a full "locator_chain" with up to 4 alternatives.

3. Detect async elements: if the page likely has loading spinners or dynamic IDs,
   add an explicit wait step BEFORE the action.

4. Include at least one assertion per test goal.

5. Sanitize all selector output — remove sensitive strings from DOM.

6. NO EMPTY SELECTORS: For interactive steps (click, fill), if no DOM is provided, GUESS the most likely selector based on common patterns (e.g., search box -> '#kw', '[name=q]', 'input[type=text]'). Never return an empty string for 'target' if the action requires one.

OUTPUT FORMAT (strict JSON array, no markdown):
[
  {
    "action": "goto|click|fill|wait|wait_for_selector|hover|select|press|assert_text|assert_visible|get_text|get_attribute|set_variable|screenshot",
    "target": "selector_string",
    "value": "optional_value_or_url",
    "locator_chain": {
      "primary": "[data-testid='xxx']",
      "fallback_1": "[aria-label='xxx']",
      "fallback_2": "//relative/xpath",
      "fallback_3": "text=visible_text"
    },
    ...
  }
]
"""

SCENARIO_SYSTEM_PROMPT = """
You are a QA strategist. Given a feature description and page context, generate a comprehensive test plan.

Return a JSON object with three arrays:
{
  "happy_path": [...max 5 steps],
  "boundary": [...max 5 steps],
  "negative": [...max 5 steps]
}

IMPORTANT: Limit each array to a maximum of 5 most critical steps. Total response must be concise.
Each step follows the same schema as standard test steps with locator_chain and assertions.
Action MUST be one of: [goto, click, fill, wait, wait_for_selector, hover, select, press, assert_text, assert_visible, screenshot].
ALWAYS provide a 'target' selector for click/fill/hover actions, even if it's a generic guess like 'button:has-text("Login")' or 'input[type="text"]'.
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
        self._clients: Dict[int, AsyncOpenAI] = {}
        logger.info("Universal AI Service v4.0 initialized (DB-Driven)")
        self._action_aliases = {
            "open": "goto",
            "visit": "goto",
            "navigate": "goto",
            "跳转": "goto",
            "访问": "goto",
            "打开": "goto",
            "input": "fill",
            "type": "fill",
            "填写": "fill",
            "输入": "fill",
            "sleep": "wait",
            "等待": "wait",
            "verify": "assert_text",
            "check": "assert_text",
            "验证": "assert_text",
            "检查": "assert_text",
            "extract_text": "get_text",
            "提取文本": "get_text",
            "extract_attr": "get_attribute",
            "提取属性": "get_attribute",
        }
        self._allowed_actions = {
            "goto",
            "click",
            "fill",
            "wait",
            "wait_for_selector",
            "assert_text",
            "assert_visible",
            "screenshot",
            "hover",
            "select",
            "press",
            "get_text",
            "get_attribute",
            "set_variable",
        }

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

        # Cache clients by model ID
        if db_model.id not in self._clients:
            try:
                client = AsyncOpenAI(
                    api_key=db_model.api_key,
                    base_url=db_model.base_url,
                    timeout=120.0
                )
                self._clients[db_model.id] = client
            except Exception as e:
                logger.error(f"Failed to init AI client for {db_model.name}: {e}")
                return None, None
                
        return self._clients[db_model.id], db_model.model_identifier

    # ─── Module 1: Multimodal Step Generation ─────────────────────────────────

    async def generate_steps_from_text(
        self,
        db: AsyncSession,
        prompt: str,
        dom_snapshot: Optional[str] = None,
        screenshot_description: Optional[str] = None,
        business_rules: Optional[str] = None,
        project_memory: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate structured Playwright test steps using DB-configured model.
        """
        client, model_name = await self._get_client_from_db(db, model_id)
        
        if not client:
            logger.warning("AI client unavailable — using mock rule engine.")
            return self._mock_generate_steps(prompt)

        # Build contextual user message
        user_message = self._build_user_message(
            prompt, dom_snapshot, screenshot_description, business_rules, project_memory
        )

        try:
            logger.info(f"Generating steps | model={model_name} | prompt={prompt[:60]}...")
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SUPER_PROMPT_SYSTEM},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=3000,
            )
            raw = response.choices[0].message.content
            steps = self._parse_json_array(raw) or self._mock_generate_steps(prompt)
            return self._clean_steps(steps)
        except Exception as e:
            logger.error(f"LLM call failed ({model_name}): {e}")
            return self._clean_steps(self._mock_generate_steps(prompt))

    # ─── Module 2: Strategic Scenario Planning ────────────────────────────────

    async def generate_scenarios(
        self,
        db: AsyncSession,
        prompt: str,
        dom_snapshot: Optional[str] = None,
        project_memory: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate happy_path, boundary, and negative test scenarios.
        """
        client, model_name = await self._get_client_from_db(db, model_id)

        if not client:
            steps = self._mock_generate_steps(prompt)
            return {"happy_path": steps, "boundary": [], "negative": []}

        user_message = self._build_user_message(
            prompt, dom_snapshot, project_memory=project_memory,
            extra_instruction="Generate all three scenario types: happy_path, boundary, negative."
        )

        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SCENARIO_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.2,
                max_tokens=4000,
            )
            raw = response.choices[0].message.content
            result = self._parse_json_object(raw)
            if result and all(k in result for k in ("happy_path", "boundary", "negative")):
                return {
                    "happy_path": self._clean_steps(result["happy_path"]),
                    "boundary": self._clean_steps(result["boundary"]),
                    "negative": self._clean_steps(result["negative"]),
                }
            # Partial fallback
            steps = self._parse_json_array(raw) or []
            return {"happy_path": self._clean_steps(steps), "boundary": [], "negative": []}
        except Exception as e:
            logger.error(f"generate_scenarios failed ({model_name}): {e}")
            steps = self._mock_generate_steps(prompt)
            return {"happy_path": self._clean_steps(steps), "boundary": [], "negative": []}

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

    def _build_user_message(
        self,
        prompt: str,
        dom_snapshot: Optional[str],
        screenshot_description: Optional[str] = None,
        business_rules: Optional[str] = None,
        project_memory: Optional[Dict[str, Any]] = None,
        extra_instruction: str = ""
    ) -> str:
        msg = f"OBJECTIVE: {prompt}\n"
        if dom_snapshot:
            msg += f"\nUI CONTEXT (DOM):\n{dom_snapshot[:20000]}\n"
        if screenshot_description:
            msg += f"\nVISUAL CONTEXT:\n{screenshot_description}\n"
        if business_rules:
            msg += f"\nBUSINESS RULES:\n{business_rules}\n"
        if project_memory:
            msg += f"\nPROJECT MEMORY:\n{json.dumps(project_memory, ensure_ascii=False)}\n"
        if extra_instruction:
            msg += f"\nINSTRUCTION: {extra_instruction}\n"
        return msg

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

    def _clean_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cleaned = []
        for s in steps:
            action = self._canonical_action(s.get("action", "click"))
            target = s.get("target") or s.get("selector") or ""
            value = s.get("value", "")
            wait_ms = self._parse_wait_ms(s.get("wait_ms"), value)
            if action == "goto" and not value and target:
                value = target
                target = ""
            if action == "wait" and wait_ms is None:
                wait_ms = 1000
                value = "1000"
            cleaned.append({
                "action": action,
                "target": target,
                "selector": target,
                "value": str(value or ""),
                "wait_ms": wait_ms,
                "locator_chain": s.get("locator_chain"),
                "variable_name": s.get("variable_name"),
                "description": s.get("description", "")
            })
        return cleaned

    def _mock_generate_steps(self, prompt: str) -> List[Dict[str, Any]]:
        """Fallback rule engine."""
        p = prompt.lower()
        if "baidu" in p or "百度" in p:
            return [{"action": "goto", "target": "", "value": "https://www.baidu.com", "description": "打开百度"}]
        return [{"action": "wait", "target": "", "value": "1000", "description": "AI 暂不可用，默认等待"}]

    def _canonical_action(self, action: Any) -> str:
        raw = str(action or "").strip().lower()
        canonical = self._action_aliases.get(raw, raw)
        if canonical not in self._allowed_actions:
            if "assert" in canonical or "verify" in canonical:
                return "assert_text"
            return "click"
        return canonical

    def _parse_wait_ms(self, wait_ms: Any, value: Any) -> Optional[int]:
        source = wait_ms if wait_ms is not None else value
        if source is None:
            return None
        if isinstance(source, (int, float)):
            return int(source if source >= 100 else source * 1000)
        text = str(source).strip().lower()
        m = re.match(r"^(\d+(?:\.\d+)?)\s*(ms|s)?$", text)
        if not m:
            return None
        amount = float(m.group(1))
        unit = m.group(2)
        if unit == "ms":
            return int(amount)
        if unit == "s":
            return int(amount * 1000)
        return int(amount if amount >= 100 else amount * 1000)


ai_service = AIService()
