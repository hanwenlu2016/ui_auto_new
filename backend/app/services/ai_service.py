import os
from typing import List, Dict, Any, Optional
import json
import re
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.logger import logger

class AIService:
    """
    AI Service powered by MiniMax (OpenAI Compatible) for generating test steps,
    self-healing, and error analysis.
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
                    base_url=self.base_url
                )
                self._initialized = True
                logger.info(f"AI Service initialized with model: {self.model_name} at {self.base_url}")
            except Exception as e:
                logger.error(f"Failed to initialize AI Service: {str(e)}")

    async def generate_steps_from_text(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Generate structured Playwright test steps from natural language using LLM.
        """
        if not self._initialized:
            logger.warning("AI Service not initialized (API Key missing), falling back to mock rules.")
            return self._mock_generate_steps(prompt)

        system_prompt = """
        You are a Test Automation Expert. Convert natural language descriptions into a sequence of Playwright test steps.
        Return ONLY a JSON array of objects. Each object must have:
        - "action": One of ["goto", "click", "fill", "wait", "hover", "select", "check", "uncheck"]
        - "target": The CSS selector or text-based locator (e.g., "text=Login" or "#submit")
        - "value": (Optional) The string to type or URL to visit.
        - "description": A human-readable description of what this step does.

        Example output:
        [
          {"action": "goto", "value": "https://example.com", "description": "Navigate to the home page"},
          {"action": "fill", "target": "#username", "value": "admin", "description": "Enter username"},
          {"action": "click", "target": "text=Submit", "description": "Click the submit button"}
        ]
        """
        
        try:
            logger.info(f"Generating steps for prompt: {prompt}")
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User request: {prompt}"}
                ],
                temperature=0.1
            )
            
            text = response.choices[0].message.content
            logger.info(f"AI Raw Response: {text}")
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            logger.warning("No JSON array found in AI response")
            return []
        except Exception as e:
            logger.error(f"Error generating steps with LLM: {str(e)}", exc_info=True)
            return self._mock_generate_steps(prompt)

    async def heal_element(self, element_metadata: Dict[str, Any], page_source: str, screenshot: Optional[str] = None) -> Dict[str, Any]:
        """
        Match broken element metadata against current page source to find a new selector.
        """
        if not self._initialized:
            return {
                "new_selector": "", 
                "confidence": 0.0, 
                "explanation": "AI Service not initialized. Cannot perform healing."
            }

        truncated_source = page_source[:30000] # MiniMax context might be smaller than Gemini

        system_prompt = """
        You are a Test Automation Expert with expertise in DOM analysis and Self-healing.
        You are given:
        1. Metadata of an element that once existed (the "target").
        2. The current HTML source of the page.

        Identify the element in the current HTML that most likely represents the target element, 
        even if its ID, Class, or structure has changed.

        Return ONLY a JSON object:
        {
          "new_selector": "the most robust CSS selector for the matched element",
          "confidence": 0.95,
          "explanation": "Why this element was chosen (e.g., matching text and aria-label despite class change)"
        }
        """

        input_data = f"""
        TARGET ELEMENT METADATA:
        {json.dumps(element_metadata, indent=2)}

        CURRENT PAGE HTML (TRUNCATED):
        {truncated_source}
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_data}
                ],
                temperature=0.1
            )
            
            text = response.choices[0].message.content
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {"new_selector": "", "confidence": 0.0, "explanation": "Failed to parse AI response"}
        except Exception as e:
            logger.error(f"Error healing element with LLM: {str(e)}")
            if "429" in str(e) or "quota" in str(e).lower():
                return {
                    "new_selector": f"text='{element_metadata.get('innerText', '')}'",
                    "confidence": 0.3,
                    "explanation": f"AI Quota exceeded or error. Falling back to simple text match: {str(e)}"
                }
            return {"new_selector": "", "confidence": 0.0, "explanation": str(e)}

    def _mock_generate_steps(self, prompt: str) -> List[Dict[str, Any]]:
        """
        Simple rule-based fallback for common automation commands (supports Chinese and English).
        """
        steps = []
        # Split by common delimiters
        parts = re.split(r'\n|;|，|。|然后|接着|并', prompt)
        
        for part in parts:
            part = part.strip().lower()
            if not part: continue
            
            # 1. Navigation
            if any(w in part for w in ['访问', '打开', '跳转', 'open', 'goto', 'visit']):
                url_match = re.search(r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,})', part)
                url = url_match.group(0) if url_match else "https://www.baidu.com"
                if not url.startswith('http'): url = 'http://' + url
                steps.append({"action": "goto", "value": url, "description": f"访问网址: {url}"})
                
            # 2. Clicking
            elif any(w in part for w in ['点击', '按', 'click', 'press']):
                target = re.sub(r'点击|按|按钮|click|press|button', '', part).strip()
                if not target: target = "确认"
                steps.append({"action": "click", "target": f"text={target}", "description": f"点击元素: {target}"})
                
            # 3. Filling / Input
            elif any(w in part for w in ['输入', '填写', 'type', 'fill', 'input']):
                match = re.search(r'(?:输入|填写|input|fill)\s*(.*?)\s*(?:到|in|into)?\s*(.*)', part)
                if match:
                    val, target = match.groups()
                    if not target: target = "输入框"
                    steps.append({"action": "fill", "target": f"text={target}", "value": val, "description": f"在 {target} 输入 {val}"})
                else:
                    steps.append({"action": "fill", "target": "input", "value": "测试数据", "description": "输入默认值"})
                    
            # 4. Waiting
            elif any(w in part for w in ['等待', '停', 'wait', 'sleep']):
                sec_match = re.search(r'(\d+)', part)
                sec = int(sec_match.group(1)) if sec_match else 3
                steps.append({"action": "wait", "value": str(sec * 1000), "description": f"等待 {sec} 秒"})

        return steps

# Singleton instance
ai_service = AIService()
