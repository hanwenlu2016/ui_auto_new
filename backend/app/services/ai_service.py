import os
from typing import List, Dict, Any, Optional
import json
import re
from uuid import uuid4
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logger import logger


# ─── Prompt Templates ─────────────────────────────────────────────────────────

SUPER_PROMPT_SYSTEM = """
You are an elite UI Test Automation Engineer with 10+ years of experience.
Your mission: convert user instructions into robust, production-grade Playwright test steps.

### AI-PAGE-AGENT PROTOCOL
You are provided with a 'PROJECT_PAGES' context containing known Pages and Elements for this project.
1. PREFER EXISTING ELEMENTS: If the user instruction matches a known element name in a page, you MUST use that element's selector.
2. SELECTOR CONSISTENCY: Do not guess new selectors for elements that are already in the library.
3. DESCRIPTION ENHANCEMENT: For steps using library elements, set the "description" to: "Using [Page] -> [Element]".

### STRATEGY
1. GOAL: Generate a single, robust "Happy Path" (常规正向路径) that successfully fulfills the user's objective.

2. Prefer stable selectors (if not using Library) in this priority order:
   [data-testid] > [aria-label] > relative XPath > text= > CSS class

3. For EVERY interactive step, provide a full "locator_chain" with up to 4 alternatives.

4. Detect async elements: if the page likely has loading spinners or dynamic IDs,
   add an explicit wait step BEFORE the action.

5. Include at least one assertion per test goal.

6. NO EMPTY SELECTORS: For interactive steps (click, fill), if no DOM is provided, use semantic, execution-friendly selectors instead of site-specific legacy IDs. 

7. **INTELLIGENT AGENT MODE**: If you cannot determine a precise selector from context, and it's NOT in the library, set "target": "AI_AUTO" and provide a detailed natural language instruction in "description".

8. USE ONLY CANONICAL ACTIONS:
   goto, click, fill, wait, wait_for_selector, hover, select, press, assert_text, assert_visible, get_text, get_attribute, set_variable, screenshot

9. DO NOT output plans, reasoning, tips, or test strategy text. Output executable steps only.

10. When you use a library element, mention the exact page name and element name in description so the system can bind it back.

11. For forms and login/search flows, prefer explicit click on the visible submit/search/login button instead of assuming Enter will submit, unless DOM clearly proves Enter is correct.

12. For assert_text steps, put the expected text in "value". For assert_visible, point "target" to the element that should become visible.

OUTPUT FORMAT (strict JSON array, no markdown):
[
  {
    "action": "goto|click|fill|wait|wait_for_selector|hover|select|press|assert_text|assert_visible|get_text|get_attribute|set_variable|screenshot",
    "target": "selector_string_or_AI_AUTO",
    "value": "optional_value_or_url",
    "locator_chain": {
      "primary": "selector",
      "fallback_1": "...",
      "fallback_2": "...",
      "fallback_3": "..."
    },
    "description": "Detailed description, e.g., 'Using [Page] -> [Element]'"
  }
]
"""

STEP_EXAMPLES_BLOCK = """
Executable examples:
[
  {
    "action": "goto",
    "target": "",
    "value": "https://example.com/login",
    "description": "Open login page"
  },
  {
    "action": "fill",
    "target": "[data-testid='username']",
    "value": "admin",
    "locator_chain": {
      "primary": "[data-testid='username']",
      "fallback_1": "[name='username']",
      "fallback_2": "input[placeholder*='用户名']",
      "fallback_3": "input[type='text']"
    },
    "description": "Using LoginPage -> UsernameInput"
  },
  {
    "action": "click",
    "target": "AI_AUTO",
    "value": "",
    "description": "Click the visible login button labeled 登录 in the main form"
  },
  {
    "action": "assert_visible",
    "target": "text=工作台",
    "value": "",
    "description": "Verify dashboard is visible after login"
  }
]
"""

# SCENARIO_SYSTEM_PROMPT removed. Simplified to single path in SUPER_PROMPT_SYSTEM.

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
        result = await self.generate_steps_bundle_from_text(
            db=db,
            prompt=prompt,
            dom_snapshot=dom_snapshot,
            screenshot_description=screenshot_description,
            business_rules=business_rules,
            project_memory=project_memory,
            model_id=model_id,
        )
        return result["steps"]

    async def generate_steps_bundle_from_text(
        self,
        db: AsyncSession,
        prompt: str,
        dom_snapshot: Optional[str] = None,
        screenshot_description: Optional[str] = None,
        business_rules: Optional[str] = None,
        project_memory: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate structured Playwright test steps together with trace metadata for observability.
        """
        client, model_name = await self._get_client_from_db(db, model_id)
        trace: Dict[str, Any] = {
            "trace_id": uuid4().hex[:12],
            "model_name": model_name,
            "fallback_used": False,
            "fallback_reason": None,
            "parse_source": "none",
            "raw_response_preview": "",
            "raw_response_length": 0,
            "parsed_step_count": 0,
            "cleaned_step_count": 0,
            "final_step_count": 0,
            "interactive_step_count": 0,
            "assertion_step_count": 0,
            "ai_auto_count": 0,
            "auto_assert_added": False,
        }

        if not client:
            logger.warning("AI client unavailable — using mock rule engine.")
            fallback_steps = self._post_process_generated_steps(self._clean_steps(self._mock_generate_steps(prompt)), prompt)
            trace.update(self._summarize_steps(fallback_steps))
            trace["fallback_used"] = True
            trace["fallback_reason"] = "client_unavailable"
            return {"steps": fallback_steps, "trace": trace}

        # Build contextual user message
        user_message = self._build_user_message(
            prompt, dom_snapshot, screenshot_description, business_rules, project_memory
        )

        try:
            logger.info(f"Generating steps | model={model_name} | prompt={prompt[:60]}...")
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": f"{SUPER_PROMPT_SYSTEM}\n{STEP_EXAMPLES_BLOCK}"},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=3000,
            )
            raw = response.choices[0].message.content
            trace["raw_response_preview"] = str(raw or "")[:800]
            trace["raw_response_length"] = len(str(raw or ""))
            parsed_steps, parse_source = self._parse_steps_payload(raw)
            trace["parse_source"] = parse_source
            trace["parsed_step_count"] = len(parsed_steps or [])

            if not parsed_steps:
                trace["fallback_used"] = True
                trace["fallback_reason"] = "parse_failed"
                parsed_steps = self._mock_generate_steps(prompt)

            cleaned_steps = self._clean_steps(parsed_steps)
            trace["cleaned_step_count"] = len(cleaned_steps)
            final_steps = self._post_process_generated_steps(cleaned_steps, prompt)
            trace.update(self._summarize_steps(final_steps))
            trace["auto_assert_added"] = trace["assertion_step_count"] > sum(
                1 for step in cleaned_steps if str(step.get("action") or "") in {"assert_text", "assert_visible"}
            )
            return {"steps": final_steps, "trace": trace}
        except Exception as e:
            logger.error(f"LLM call failed ({model_name}): {e}")
            fallback_steps = self._post_process_generated_steps(self._clean_steps(self._mock_generate_steps(prompt)), prompt)
            trace.update(self._summarize_steps(fallback_steps))
            trace["fallback_used"] = True
            trace["fallback_reason"] = f"llm_error:{type(e).__name__}"
            return {"steps": fallback_steps, "trace": trace}

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
            # 1. Past corrections & feedback
            feedbacks = project_memory.get("feedbacks", [])
            if feedbacks:
                msg += "\nPROJECT FEEDBACK (PAST CORRECTIONS):\n"
                for i, fb in enumerate(feedbacks, 1):
                    msg += f"{i}. {fb['ai_notes']} | {fb['comment']}\n"

            healing_memories = project_memory.get("healing_memories", [])
            if healing_memories:
                msg += "\nPROJECT HEALING MEMORY (VERIFIED SELECTOR RECOVERY):\n"
                for i, heal in enumerate(healing_memories, 1):
                    confidence = heal.get("confidence")
                    confidence_text = f" | confidence={confidence:.2f}" if isinstance(confidence, (int, float)) else ""
                    msg += (
                        f"{i}. [{heal['page_name']}] {heal['element_name']} | "
                        f"old={heal['original_selector']} | learned={heal['healed_selector']}"
                        f"{confidence_text}"
                    )
                    if heal.get("change_summary"):
                        msg += f" | note={heal['change_summary']}"
                    msg += "\n"
            
            # 2. Page Object Library (Page-Agent Context)
            library = project_memory.get("page_object_library", [])
            if library:
                msg += "\nPROJECT_PAGES (Page-Agent Known Library):\n"
                for p in library:
                    msg += f"Page: {p['page_name']}\n"
                    for e in p['elements']:
                        desc = f" ({e['description']})" if e['description'] else ""
                        alt = [s for s in (e.get("selectors") or []) if s != e.get("selector")]
                        alt_text = f" | AltSelectors: {', '.join(alt[:3])}" if alt else ""
                        msg += f"  - Element: {e['name']} | Selector: {e['selector']} | Type: {e['type']}{desc}{alt_text}\n"

        if extra_instruction:
            msg += f"\nINSTRUCTION: {extra_instruction}\n"
        return msg

    def _parse_json_array(self, text: str) -> Optional[List[Dict[str, Any]]]:
        try:
            # Look for [ ... ]
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end != -1:
                payload = json.loads(text[start:end])
                if isinstance(payload, list):
                    return payload
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

    def _parse_steps_payload(self, text: str) -> tuple[Optional[List[Dict[str, Any]]], str]:
        payload = self._parse_json_array(text)
        if payload:
            return payload, "array"

        obj = self._parse_json_object(text)
        if not isinstance(obj, dict):
            return None, "none"

        for key in ("steps", "data", "result"):
            value = obj.get(key)
            if isinstance(value, list):
                return value, key
            if isinstance(value, dict):
                for nested_key in ("steps", "items", "data", "result"):
                    nested_value = value.get(nested_key)
                    if isinstance(nested_value, list):
                        return nested_value, f"{key}.{nested_key}"
        return None, "object_without_steps"

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

    def _post_process_generated_steps(self, steps: List[Dict[str, Any]], prompt: str) -> List[Dict[str, Any]]:
        processed: List[Dict[str, Any]] = []
        prompt_text = str(prompt or "").strip()
        interactive_actions = {"click", "fill", "select", "hover", "press", "wait_for_selector"}
        assertion_actions = {"assert_text", "assert_visible"}

        for step in steps:
            next_step = dict(step)
            action = str(next_step.get("action") or "").strip()
            locator_chain = next_step.get("locator_chain")
            target = str(next_step.get("target") or "").strip()
            description = str(next_step.get("description") or "").strip()

            if not target and isinstance(locator_chain, dict):
                primary = str(locator_chain.get("primary") or "").strip()
                if primary:
                    target = primary

            if action in interactive_actions and not target:
                target = "AI_AUTO"

            if target:
                next_step["target"] = target
                next_step["selector"] = target

            if not description:
                description = self._build_step_description(next_step, prompt_text)

            if action in interactive_actions and target == "AI_AUTO" and "using " not in description.lower():
                description = description or self._build_step_description(next_step, prompt_text)

            next_step["description"] = description
            processed.append(next_step)

        if not processed:
            return processed

        if not any(str(step.get("action") or "") in assertion_actions for step in processed):
            last_target = ""
            for step in reversed(processed):
                candidate = str(step.get("target") or "").strip()
                if candidate and candidate != "AI_AUTO":
                    last_target = candidate
                    break
            processed.append({
                "action": "assert_visible",
                "target": last_target or "AI_AUTO",
                "selector": last_target or "AI_AUTO",
                "value": "",
                "wait_ms": None,
                "locator_chain": {"primary": last_target} if last_target else None,
                "variable_name": None,
                "description": "Verify the expected result is visible after completing the flow"
            })

        return processed

    def _summarize_steps(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        interactive_actions = {"click", "fill", "select", "hover", "press", "wait_for_selector"}
        assertion_actions = {"assert_text", "assert_visible"}
        return {
            "final_step_count": len(steps),
            "interactive_step_count": sum(
                1 for step in steps if str(step.get("action") or "") in interactive_actions
            ),
            "assertion_step_count": sum(
                1 for step in steps if str(step.get("action") or "") in assertion_actions
            ),
            "ai_auto_count": sum(
                1 for step in steps if str(step.get("target") or "").strip() == "AI_AUTO"
            ),
        }

    def _build_step_description(self, step: Dict[str, Any], prompt: str) -> str:
        action = str(step.get("action") or "").strip()
        target = str(step.get("target") or "").strip()
        value = str(step.get("value") or "").strip()

        if action == "goto":
            return f"Open {value or prompt or 'the target page'}".strip()
        if action == "fill":
            if target == "AI_AUTO":
                return f"Fill the relevant input field for: {prompt or value or 'the requested data'}"
            return f"Fill {target} with {value}" if value else f"Fill {target}"
        if action == "click":
            if target == "AI_AUTO":
                return f"Click the control needed to complete: {prompt or 'the current task'}"
            return f"Click {target}"
        if action == "wait":
            return f"Wait {value or '1000'} milliseconds for the page to stabilize"
        if action == "wait_for_selector":
            if target == "AI_AUTO":
                return "Wait until the expected target element appears"
            return f"Wait for {target} to appear"
        if action == "assert_text":
            if target and target != "AI_AUTO":
                return f"Verify {target} contains expected text"
            return f"Verify the page contains expected text: {value or prompt}"
        if action == "assert_visible":
            if target and target != "AI_AUTO":
                return f"Verify {target} is visible"
            return "Verify the expected result is visible"
        if action == "select":
            return f"Select {value} in {target}" if value and target else "Select the requested option"
        if action == "press":
            return f"Press {value} on {target}" if value and target else f"Press {value or 'the requested key'}"
        if action == "get_text":
            return f"Read text from {target}" if target else "Read text from the current page"
        if action == "get_attribute":
            return f"Read attribute from {target}" if target else "Read the requested attribute"
        if action == "screenshot":
            return "Capture a screenshot for verification"
        return prompt or "Execute the requested UI action"

    def _mock_generate_steps(self, prompt: str) -> List[Dict[str, Any]]:
        """Fallback rule engine for common patterns when LLM is down."""
        p = prompt.lower()
        steps = []
        if "baidu" in p or "百度" in p:
            steps.append({"action": "goto", "target": "", "value": "https://www.baidu.com", "description": "打开百度"})
        
        if "login" in p or "登录" in p:
            if not steps: # If no explicit URL, assume current
                steps.append({"action": "click", "target": "input[type='text'], input[placeholder*='账号'], #username", "value": "", "description": "点击账号输入框"})
            steps.append({"action": "fill", "target": "input[type='text'], #username", "value": "admin", "description": "输入默认账号"})
            steps.append({"action": "fill", "target": "input[type='password'], #password", "value": "admin", "description": "输入默认密码"})
            steps.append({"action": "click", "target": "button[type='submit'], .login-btn, #login", "value": "", "description": "点击登录按钮"})
            
        if not steps:
            steps.append({"action": "wait", "target": "", "value": "1000", "description": "AI 暂不可用 (API 429 频率限制)，请稍后重试或检查 API 配额。"})
            
        return steps

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
