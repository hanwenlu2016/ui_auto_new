import os
from typing import List, Dict, Any, Optional
import json
import re
from openai import AsyncOpenAI
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
    "action": "goto|click|fill|wait|hover|select|assert_text|screenshot",
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
Action MUST be one of: [goto, click, fill, assert_text, wait, hover, select, screenshot].
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
    Enhanced AI Service — v2.0
    Powers 4 core capabilities:
      1. Multimodal context-aware step generation (Super-Prompt)
      2. Strategic test scenario planning (happy/boundary/negative)
      3. Self-healing with prioritized locator chain
      4. Project memory injection for RLHF
    """

    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.base_url = settings.AI_BASE_URL
        self.model_name = settings.AI_MODEL
        self._initialized = False

        if self.api_key:
            try:
                self.client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=120.0
                )
                self._initialized = True
                logger.info(f"AI Service v2 initialized: {self.model_name} @ {self.base_url}")
            except Exception as e:
                logger.error(f"AI Service init failed: {e}")

    # ─── Module 1: Multimodal Step Generation ─────────────────────────────────

    async def generate_steps_from_text(
        self,
        prompt: str,
        dom_snapshot: Optional[str] = None,
        screenshot_description: Optional[str] = None,
        business_rules: Optional[str] = None,
        project_memory: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate structured Playwright test steps with rich context injection.
        Falls back to rule-based mock if AI is unavailable.
        """
        if not self._initialized:
            logger.warning("AI not initialized — using mock rule engine.")
            return self._mock_generate_steps(prompt)

        # Build contextual user message
        user_message = self._build_user_message(
            prompt, dom_snapshot, screenshot_description, business_rules, project_memory
        )

        try:
            logger.info(f"Generating steps | prompt={prompt[:100]!r}")
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SUPER_PROMPT_SYSTEM},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=3000,
            )
            raw = response.choices[0].message.content
            logger.info(f"AI raw response (first 300 chars): {raw[:300]}")
            steps = self._parse_json_array(raw) or self._mock_generate_steps(prompt)
            return self._clean_steps(steps)
        except Exception as e:
            logger.error(f"LLM call failed: {e}", exc_info=True)
            return self._clean_steps(self._mock_generate_steps(prompt))

    # ─── Module 2: Strategic Scenario Planning ────────────────────────────────

    async def generate_scenarios(
        self,
        prompt: str,
        dom_snapshot: Optional[str] = None,
        project_memory: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate happy_path, boundary, and negative test scenarios in one call.
        """
        if not self._initialized:
            steps = self._mock_generate_steps(prompt)
            return {"happy_path": steps, "boundary": [], "negative": []}

        user_message = self._build_user_message(
            prompt, dom_snapshot, project_memory=project_memory,
            extra_instruction="Generate all three scenario types: happy_path, boundary, negative."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
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
            # Partial fallback: wrap everything as happy_path
            steps = self._parse_json_array(raw) or []
            return {"happy_path": self._clean_steps(steps), "boundary": [], "negative": []}
        except Exception as e:
            logger.error(f"generate_scenarios failed: {e}", exc_info=True)
            steps = self._mock_generate_steps(prompt)
            return {"happy_path": self._clean_steps(steps), "boundary": [], "negative": []}

    # ─── Module 3: Self-Healing with Locator Chain ───────────────────────────

    async def heal_element(
        self,
        element_metadata: Dict[str, Any],
        page_source: str,
        screenshot_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        AI-powered element healing.
        Returns a prioritized locator_chain with confidence score.
        Falls back to simple text match if AI unavailable.
        """
        if not self._initialized:
            text = element_metadata.get("innerText", "")
            return {
                "locator_chain": {
                    "primary": f"text={text}",
                    "fallback_1": None, "fallback_2": None,
                    "fallback_3": None, "fallback_image": None,
                },
                "confidence": 0.2,
                "change_summary": "AI unavailable — text match fallback.",
                "explanation": "No AI service.",
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
            response = await self.client.chat.completions.create(
                model=self.model_name,
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
            logger.error(f"heal_element failed: {e}", exc_info=True)
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

    # ─── Module 4: Project Memory (RLHF support) ─────────────────────────────

    def build_project_memory_context(self, feedbacks: List[Dict[str, Any]]) -> str:
        """
        Converts stored StepFeedback records into a concise memory string
        to be injected into future Prompts for this project.
        """
        if not feedbacks:
            return ""

        corrections = [f for f in feedbacks if f.get("feedback_type") == "correction"]
        thumbs_up = [f for f in feedbacks if f.get("feedback_type") == "thumbs_up"]

        lines = ["[PROJECT MEMORY — learned from past feedback]"]
        if corrections:
            lines.append("Known corrections:")
            for c in corrections[:5]:
                notes = c.get("ai_notes") or ""
                if notes:
                    lines.append(f"  - {notes}")
        if thumbs_up:
            lines.append(f"Previously approved patterns: {len(thumbs_up)} confirmed steps.")

        return "\n".join(lines)

    # ─── Private Helpers ──────────────────────────────────────────────────────

    def _build_user_message(
        self,
        prompt: str,
        dom_snapshot: Optional[str] = None,
        screenshot_description: Optional[str] = None,
        business_rules: Optional[str] = None,
        project_memory: Optional[Dict[str, Any]] = None,
        extra_instruction: Optional[str] = None,
    ) -> str:
        parts = []

        if project_memory:
            memory_ctx = self.build_project_memory_context(
                project_memory.get("feedbacks", [])
            )
            if memory_ctx:
                parts.append(memory_ctx)

        if business_rules:
            parts.append(f"[BUSINESS RULES]\n{business_rules}")

        if dom_snapshot:
            # Truncate DOM to avoid context overflow; keep top 100 lines for faster reasoning
            dom_lines = dom_snapshot.splitlines()[:100]
            sanitized = "\n".join(dom_lines)
            parts.append(f"[PAGE DOM SNAPSHOT — top 100 lines, sanitized]\n{sanitized}")

        if screenshot_description:
            parts.append(f"[SCREENSHOT DESCRIPTION]\n{screenshot_description}")

        parts.append(f"[USER INSTRUCTION]\n{prompt}")

        if extra_instruction:
            parts.append(f"[EXTRA INSTRUCTION]\n{extra_instruction}")

        return "\n\n".join(parts)

    def _parse_json_array(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """Extract first JSON array from raw LLM response."""
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as e:
                logger.warning(f"JSON array parse error: {e}")
        return None

    def _parse_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract first JSON object from raw LLM response."""
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as e:
                logger.warning(f"JSON object parse error: {e}")
        return None

    def _mock_generate_steps(self, prompt: str) -> List[Dict[str, Any]]:
        """
        Rule-based fallback for common automation commands.
        Supports both Chinese and English.
        """
        steps = []
        parts = re.split(r'\n|;|，|。|然后|接着|并', prompt)

        for part in parts:
            part = part.strip().lower()
            if not part:
                continue

            if any(w in part for w in ['访问', '打开', '跳转', 'open', 'goto', 'visit']):
                # 更严谨的 URL 匹配，并尝试移除末尾的干扰项（如 54ms, (123ms) 等）
                url_match = re.search(r'(https?://[^\s\)]+|www\.[^\s\)]+)', part)
                if url_match:
                    url = url_match.group(0)
                    # 剔除末尾可能带有的数字+ms后缀（AI推理耗时残留）
                    url = re.sub(r'(\d+ms|\d+s|\d+ms\)?)$', '', url).rstrip('./),')
                else:
                    url = "https://www.baidu.com"

                if not url.startswith('http') and url:
                    url = 'https://' + url
                steps.append({
                    "action": "goto",
                    "value": url,
                    "locator_chain": {},
                    "wait_strategy": {"type": "network_idle", "timeout_ms": 10000},
                    "assertion": {"type": "url_contains", "expected": url[:30]},
                    "scenario_type": "happy_path",
                    "description": f"访问网址: {url}",
                })

            elif any(w in part for w in ['点击', '按', 'click', 'press']):
                target = re.sub(r'点击|按|按钮|click|press|button', '', part).strip() or "确认"
                steps.append({
                    "action": "click",
                    "target": f"text={target}",
                    "locator_chain": {
                        "primary": f"[aria-label='{target}']",
                        "fallback_1": f"text={target}",
                        "fallback_2": f"//button[contains(.,'{target}')]",
                        "fallback_3": None,
                    },
                    "wait_strategy": {"type": "element_visible", "selector": f"text={target}", "timeout_ms": 5000},
                    "assertion": {"type": "element_exists", "expected": "action completed"},
                    "scenario_type": "happy_path",
                    "description": f"点击元素: {target}",
                })

            elif any(w in part for w in ['输入', '填写', 'type', 'fill', 'input']):
                match = re.search(r'(?:输入|填写|input|fill)\s*(.*?)\s*(?:到|in|into)?\s*(.*)', part)
                val, target = match.groups() if match else ("测试数据", "输入框")
                if not target:
                    target = "输入框"
                steps.append({
                    "action": "fill",
                    "target": f"text={target}",
                    "value": val,
                    "locator_chain": {
                        "primary": f"[placeholder*='{target}']",
                        "fallback_1": f"[aria-label*='{target}']",
                        "fallback_2": f"//input[contains(@placeholder,'{target}')]",
                        "fallback_3": None,
                    },
                    "wait_strategy": {"type": "element_visible", "selector": f"text={target}", "timeout_ms": 5000},
                    "assertion": {"type": "attribute", "expected": f"value={val}"},
                    "scenario_type": "happy_path",
                    "description": f"在 {target} 输入: {val}",
                })

            elif any(w in part for w in ['等待', '停', 'wait', 'sleep']):
                sec_match = re.search(r'(\d+)', part)
                ms = int(sec_match.group(1)) * 1000 if sec_match else 3000
                steps.append({
                    "action": "wait",
                    "value": str(ms),
                    "wait_strategy": {"type": "custom_timeout", "timeout_ms": ms},
                    "locator_chain": {},
                    "assertion": {},
                    "scenario_type": "happy_path",
                    "description": f"等待 {ms // 1000} 秒",
                })

        return steps


    def _clean_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """彻底清洗步骤中的所有字符串字段，移除类似 239ms 的推理残留文字，并确保字段对齐"""
        import re
        noise_pattern = re.compile(r'(\s*\(?\d+\.?\d*m?s\)?\s*)$', re.IGNORECASE)
        
        for step in steps:
            # 1. 字段对齐: 确保 goto 的 URL 在 value 字段
            act = (step.get("action") or "").lower()
            val = step.get("value") or ""
            tar = step.get("target") or step.get("selector") or ""
            
            if any(x in act for x in ["goto", "跳转", "访问", "打开"]) and not val and tar:
                step["value"] = tar
                step["target"] = ""
            
            # 2. 字段清洗
            for field in ["target", "value", "action"]:
                if field in step and isinstance(step[field], str):
                    # 移除末尾的时间后缀
                    step[field] = noise_pattern.sub('', step[field]).strip()
                    
                    # 如果是 goto 类型，额外清理 URL 常见的异常后缀
                    if field == "value" and any(x in act for x in ["goto", "跳转", "访问", "打开"]):
                        step[field] = re.sub(r'(\d+ms|\d+s|ms|s)$', '', step[field]).rstrip('./),')
        return steps

# Singleton
ai_service = AIService()
