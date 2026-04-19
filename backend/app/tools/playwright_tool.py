"""
Playwright automation tool for browser interactions.
Provides a clean interface for common browser automation tasks.
"""
import asyncio
import logging
import re
import time
from typing import Optional, Dict, Any, List, Tuple
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Locator, expect

logger = logging.getLogger(__name__)


class PlaywrightTool:
    """
    Playwright automation tool for managing browser interactions.
    Provides methods for common actions like navigation, clicking, filling forms, etc.
    """
    
    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        """
        Initialize PlaywrightTool.
        
        Args:
            headless: Whether to run browser in headless mode
            browser_type: Browser type - "chromium", "firefox", or "webkit"
        """
        self.headless = headless
        self.browser_type = browser_type
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def __aenter__(self):
        """Context manager entry - initialize browser."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup browser."""
        await self.close()
    
    async def start(self):
        """Start Playwright and launch browser."""
        self.playwright = await async_playwright().start()
        
        # Launch appropriate browser based on browser_type
        if self.browser_type == "firefox":
            self.browser = await self.playwright.firefox.launch(headless=self.headless)
        elif self.browser_type == "webkit":
            self.browser = await self.playwright.webkit.launch(headless=self.headless)
        else:  # default to chromium
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
        
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        logger.info(f"Playwright browser started: {self.browser_type}, headless={self.headless}")
    
    async def close(self):
        """Close browser and cleanup resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright browser closed")
    
    async def goto(self, url: str, **kwargs) -> None:
        """
        Navigate to a URL.
        
        Args:
            url: The URL to navigate to
            **kwargs: Additional arguments for page.goto()
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        # Set default timeout to 60 seconds if not specified
        if "timeout" not in kwargs:
            kwargs["timeout"] = 60000
            
        await self.page.goto(url, **kwargs)
        logger.debug(f"Navigated to {url}")

    def _strip_visible_pseudo(self, selector: str) -> str:
        return re.sub(r":visible\b", "", selector or "", flags=re.IGNORECASE).strip()

    async def _get_preferred_locator(
        self,
        selector: str,
        *,
        timeout: int = 10000,
        require_visible: bool = True,
        max_candidates: int = 10,
    ) -> Locator:
        """
        Resolve a selector to a concrete locator.
        Prefer a visible match when multiple nodes or hidden duplicates exist.
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        candidates = [selector]
        stripped = self._strip_visible_pseudo(selector)
        if stripped and stripped != selector:
            candidates.append(stripped)

        deadline = time.monotonic() + (timeout / 1000)
        last_count = 0

        while time.monotonic() < deadline:
            for candidate in candidates:
                locator = self.page.locator(candidate)
                count = await locator.count()
                last_count = max(last_count, count)
                if count == 0:
                    continue

                if not require_visible:
                    return locator.first

                for idx in range(min(count, max_candidates)):
                    item = locator.nth(idx)
                    try:
                        if await item.is_visible():
                            return item
                    except Exception:
                        continue

            await asyncio.sleep(0.2)

        visibility_hint = "visible " if require_visible else ""
        raise TimeoutError(
            f"No {visibility_hint}element resolved for selector '{selector}' within {timeout}ms; matched_count={last_count}"
        )

    def _extract_hint_tokens(
        self,
        selector: str,
        step_description: Optional[str] = None,
        value: Optional[str] = None,
    ) -> List[str]:
        combined = " ".join(
            [
                str(selector or ""),
                str(step_description or ""),
                str(value or ""),
                str(self.page.url if self.page else ""),
            ]
        ).lower()
        raw_tokens = re.findall(r"[a-z0-9_]{2,}", combined)
        tokens: List[str] = []
        stop_words = {
            "visible",
            "selector",
            "target",
            "input",
            "click",
            "fill",
            "wait",
            "assert",
            "text",
            "element",
            "timeout",
            "http",
            "https",
            "www",
            "com",
        }
        for token in raw_tokens:
            if token in stop_words:
                continue
            if token not in tokens:
                tokens.append(token)
        for term in ["搜索", "百度", "输入", "提交", "结果"]:
            if term in combined and term not in tokens:
                tokens.append(term)
        return tokens

    def _looks_like_search_intent(
        self,
        action: str,
        selector: str,
        step_description: Optional[str] = None,
        value: Optional[str] = None,
    ) -> bool:
        combined = " ".join(
            [
                str(action or ""),
                str(selector or ""),
                str(step_description or ""),
                str(value or ""),
                str(self.page.url if self.page else ""),
            ]
        ).lower()
        search_markers = [
            "search",
            "query",
            "keyword",
            "textbox",
            "searchbox",
            "搜索",
            "百度",
            "kw",
            "wd",
            "name=q",
            "[name=q]",
        ]
        return any(marker in combined for marker in search_markers)

    async def _collect_semantic_candidates(self, kind: str) -> List[Dict[str, Any]]:
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        return await self.page.evaluate(
            """
            (kind) => {
              const cssEscape = (value) => {
                const text = String(value ?? '');
                if (window.CSS && typeof window.CSS.escape === 'function') {
                  return CSS.escape(text);
                }
                return text.replace(/([ !"#$%&'()*+,./:;<=>?@[\\\\\\]^`{|}~])/g, '\\\\$1');
              };
              const quoteAttr = (value) => JSON.stringify(String(value ?? ''));
              const isVisible = (el) => {
                if (!(el instanceof Element)) return false;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                const rect = el.getBoundingClientRect();
                if (rect.width < 4 || rect.height < 4) return false;
                const cx = rect.left + rect.width / 2;
                const cy = rect.top + rect.height / 2;
                if (cx < 0 || cy < 0 || cx > window.innerWidth || cy > window.innerHeight) return false;
                return true;
              };
              const buildSelector = (el) => {
                if (el.id) {
                  const byId = `#${cssEscape(el.id)}`;
                  if (document.querySelectorAll(byId).length === 1) return byId;
                }
                const tag = el.tagName.toLowerCase();
                for (const attr of ['data-testid', 'data-test', 'data-qa', 'name', 'aria-label', 'placeholder', 'title']) {
                  const value = el.getAttribute(attr);
                  if (!value) continue;
                  const candidate = `${tag}[${attr}=${quoteAttr(value)}]`;
                  if (document.querySelectorAll(candidate).length === 1) return candidate;
                }
                const stableClasses = Array.from(el.classList || [])
                  .filter((name) => name && !/^(active|focus|hover|selected|disabled|hidden|show|open|close)$/i.test(name))
                  .slice(0, 2);
                if (stableClasses.length > 0) {
                  const byClass = `${tag}${stableClasses.map((name) => `.${cssEscape(name)}`).join('')}`;
                  if (document.querySelectorAll(byClass).length === 1) return byClass;
                }
                const parts = [];
                let node = el;
                while (node && node.nodeType === 1 && parts.length < 6) {
                  const nodeTag = node.tagName.toLowerCase();
                  if (node.id) {
                    parts.unshift(`#${cssEscape(node.id)}`);
                    break;
                  }
                  let part = nodeTag;
                  const parent = node.parentElement;
                  if (parent) {
                    const siblings = Array.from(parent.children).filter((child) => child.tagName === node.tagName);
                    if (siblings.length > 1) {
                      part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
                    }
                  }
                  parts.unshift(part);
                  node = parent;
                }
                return parts.join(' > ');
              };
              const selectorMap = {
                editable: "textarea, input:not([type='hidden']), [contenteditable='true'], [role='textbox'], [role='searchbox']",
                clickable: "button, [role='button'], input[type='submit'], input[type='button'], a[href], summary"
              };
              const rootSelector = selectorMap[kind] || selectorMap.editable;
              return Array.from(document.querySelectorAll(rootSelector))
                .slice(0, 60)
                .map((el) => {
                  const rect = el.getBoundingClientRect();
                  return {
                    selector: buildSelector(el),
                    tag: el.tagName.toLowerCase(),
                    type: (el.getAttribute('type') || '').toLowerCase(),
                    id: el.id || '',
                    name: el.getAttribute('name') || '',
                    placeholder: el.getAttribute('placeholder') || el.getAttribute('data-normal-placeholder') || el.getAttribute('data-ai-placeholder') || '',
                    aria_label: el.getAttribute('aria-label') || '',
                    title: el.getAttribute('title') || '',
                    class_name: el.className || '',
                    text: (el.innerText || el.textContent || '').trim().slice(0, 120),
                    role: el.getAttribute('role') || '',
                    disabled: !!el.disabled,
                    read_only: !!el.readOnly,
                    editable: el.matches('textarea, input, [contenteditable=\"true\"], [role=\"textbox\"], [role=\"searchbox\"]'),
                    visible: isVisible(el),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    x: Math.round(rect.left),
                    y: Math.round(rect.top),
                    viewport_width: window.innerWidth,
                    viewport_height: window.innerHeight
                  };
                })
                .filter((item) => item.visible && item.selector);
            }
            """,
            kind,
        )

    def _score_semantic_candidate(
        self,
        candidate: Dict[str, Any],
        *,
        action: str,
        selector: str,
        step_description: Optional[str] = None,
        value: Optional[str] = None,
    ) -> float:
        url = str(self.page.url if self.page else "").lower()
        text_blob = " ".join(
            [
                str(candidate.get("selector", "")),
                str(candidate.get("tag", "")),
                str(candidate.get("type", "")),
                str(candidate.get("id", "")),
                str(candidate.get("name", "")),
                str(candidate.get("placeholder", "")),
                str(candidate.get("aria_label", "")),
                str(candidate.get("title", "")),
                str(candidate.get("class_name", "")),
                str(candidate.get("text", "")),
                str(candidate.get("role", "")),
            ]
        ).lower()
        score = 0.0

        if candidate.get("visible"):
            score += 10
        if candidate.get("editable"):
            score += 18
        if not candidate.get("disabled"):
            score += 6
        if not candidate.get("read_only"):
            score += 6
        if candidate.get("tag") in {"input", "textarea"}:
            score += 10

        width = float(candidate.get("width") or 0)
        height = float(candidate.get("height") or 0)
        x = float(candidate.get("x") or 0)
        y = float(candidate.get("y") or 0)
        viewport_width = float(candidate.get("viewport_width") or 1)
        viewport_height = float(candidate.get("viewport_height") or 1)
        center_x = x + width / 2
        center_y = y + height / 2
        score += min(width / 40, 12)
        score += min(height / 20, 6)
        score += max(0, 12 - abs(center_x - viewport_width / 2) / 80)
        score += max(0, 8 - abs(center_y - viewport_height * 0.35) / 80)

        search_intent = self._looks_like_search_intent(action, selector, step_description, value)
        if search_intent:
            if candidate.get("tag") == "textarea":
                score += 12
            if candidate.get("role") == "searchbox":
                score += 10
            for term in ["search", "query", "keyword", "搜索", "百度", "chat", "submit", "搜索词"]:
                if term in text_blob:
                    score += 8
            if candidate.get("placeholder"):
                score += 6

        for token in self._extract_hint_tokens(selector, step_description, value):
            if token and token in text_blob:
                score += 5

        return score

    async def _find_semantic_selector(
        self,
        *,
        action: str,
        selector: str,
        value: Optional[str] = None,
        step_description: Optional[str] = None,
    ) -> Optional[str]:
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        kind: Optional[str] = None
        if action in {"fill", "press", "select"}:
            kind = "editable"
        elif action == "wait_for_selector":
            if self._looks_like_search_intent(action, selector, step_description, value):
                kind = "editable"
        elif action in {"click", "hover"}:
            kind = "clickable"

        if not kind:
            return None

        candidates = await self._collect_semantic_candidates(kind)
        if not candidates:
            return None

        scored = sorted(
            (
                (self._score_semantic_candidate(
                    candidate,
                    action=action,
                    selector=selector,
                    step_description=step_description,
                    value=value,
                ), candidate)
                for candidate in candidates
            ),
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best_candidate = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0.0
        search_intent = self._looks_like_search_intent(action, selector, step_description, value)
        if len(candidates) == 1 and best_score >= 18:
            return best_candidate.get("selector")
        if search_intent and best_score >= 24:
            return best_candidate.get("selector")
        if best_score >= 34 and (best_score - second_score) >= 6:
            return best_candidate.get("selector")
        return None

    async def _resolve_locator(
        self,
        selector: str,
        *,
        action: str,
        timeout: int = 10000,
        require_visible: bool = True,
        value: Optional[str] = None,
        step_description: Optional[str] = None,
    ) -> Tuple[Locator, str]:
        try:
            locator = await self._get_preferred_locator(
                selector,
                timeout=timeout,
                require_visible=require_visible,
            )
            return locator, selector
        except Exception as original_error:
            healed_selector = await self._find_semantic_selector(
                action=action,
                selector=selector,
                value=value,
                step_description=step_description,
            )
            if healed_selector and healed_selector != selector:
                locator = await self._get_preferred_locator(
                    healed_selector,
                    timeout=timeout,
                    require_visible=require_visible,
                )
                logger.info(
                    "Semantic locator recovery succeeded | action=%s original=%s healed=%s",
                    action,
                    selector,
                    healed_selector,
                )
                return locator, healed_selector
            raise original_error

    
    async def click(self, selector: str, **kwargs) -> str:
        """
        Click an element, with JS fallback for headless visibility issues.
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        timeout = int(kwargs.pop("timeout", 10000))
        step_description = str(kwargs.pop("step_description", "") or "")
        try:
            locator, resolved_selector = await self._resolve_locator(
                selector,
                action="click",
                timeout=timeout,
                require_visible=True,
                step_description=step_description,
            )
            await locator.click(timeout=timeout, **kwargs)
            logger.debug(f"Clicked element: {selector}")
            return resolved_selector
        except Exception as e:
            if "Timeout" in str(e) or "visible" in str(e).lower() or "intercepted" in str(e).lower():
                logger.warning(f"Standard click failed or timed out for {selector}, attempting JS fallback: {e}")
                locator, resolved_selector = await self._resolve_locator(
                    selector, action="click", timeout=5000, require_visible=False, step_description=step_description
                )
                await locator.first.evaluate("el => el.click()")
                logger.info(f"JS fallback click succeeded for {selector}")
                return resolved_selector
            raise e
    
    async def fill(self, selector: str, value: str, **kwargs) -> str:
        """
        Fill an input field, with JS fallback for headless visibility issues.
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        timeout = int(kwargs.pop("timeout", 10000))
        step_description = str(kwargs.pop("step_description", "") or "")
        try:
            locator, resolved_selector = await self._resolve_locator(
                selector,
                action="fill",
                timeout=timeout,
                require_visible=True,
                value=value,
                step_description=step_description,
            )
            await locator.fill(value, timeout=timeout, **kwargs)
            logger.debug(f"Filled element {selector} with: {value}")
            return resolved_selector
        except Exception as e:
            if "Timeout" in str(e) or "visible" in str(e).lower() or "intercepted" in str(e).lower():
                logger.warning(f"Standard fill failed or timed out for {selector}, attempting JS fallback: {e}")
                locator, resolved_selector = await self._resolve_locator(
                    selector, action="fill", timeout=5000, require_visible=False, value=value, step_description=step_description
                )
                await locator.first.evaluate("(el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }", value)
                logger.info(f"JS fallback fill succeeded for {selector}")
                return resolved_selector
            raise e
    
    async def wait(self, milliseconds: int) -> None:
        """
        Wait for a specified duration.
        
        Args:
            milliseconds: Duration to wait in milliseconds
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        await self.page.wait_for_timeout(milliseconds)
        logger.debug(f"Waited for {milliseconds}ms")
    
    async def get_text(self, selector: str) -> Optional[str]:
        """
        Get text content of an element.
        
        Args:
            selector: CSS selector or XPath
            
        Returns:
            The text content or None
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        locator = await self._get_preferred_locator(selector, timeout=10000, require_visible=False)
        text = await locator.text_content()
        logger.debug(f"Got text from {selector}: {text}")
        return text
    
    async def assert_text(self, selector: str, expected_text: str) -> None:
        """
        Assert that an element contains expected text.
        
        Args:
            selector: CSS selector or XPath
            expected_text: The expected text
            
        Raises:
            AssertionError: If text doesn't match
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        locator = await self._get_preferred_locator(selector, timeout=10000, require_visible=False)
        await expect(locator).to_have_text(expected_text)
        logger.debug(f"Asserted text in {selector}: {expected_text}")

    async def assert_text_contains(self, selector: str, expected_text: str) -> None:
        """Assert that an element contains expected text."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        locator = await self._get_preferred_locator(selector, timeout=10000, require_visible=False)
        await expect(locator).to_contain_text(expected_text)
        logger.debug(f"Asserted text contains in {selector}: {expected_text}")

    async def assert_visible(self, selector: str, timeout: int = 10000, step_description: str = "") -> str:
        """Assert an element is visible."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        locator, resolved_selector = await self._resolve_locator(
            selector,
            action="assert_visible",
            timeout=timeout,
            require_visible=True,
            step_description=step_description,
        )
        await expect(locator).to_be_visible(timeout=timeout)
        logger.debug(f"Asserted visible: {selector}")
        return resolved_selector

    async def wait_for_selector(
        self,
        selector: str,
        timeout: int = 10000,
        state: str = "visible",
        *,
        step_description: str = "",
        value: Optional[str] = None,
    ) -> str:
        """Wait for selector to reach state, with DOM presence fallback."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        require_visible = state == "visible"
        try:
            locator, resolved_selector = await self._resolve_locator(
                selector,
                action="wait_for_selector",
                timeout=timeout,
                require_visible=require_visible,
                value=value,
                step_description=step_description,
            )
            await locator.first.wait_for(timeout=timeout, state=state)
            logger.debug(f"Waited for selector: {selector}, timeout={timeout}, state={state}")
            return resolved_selector
        except Exception as e:
            if require_visible and ("Timeout" in str(e) or "visible" in str(e).lower()):
                logger.warning(f"wait_for_selector(visible) failed for {selector}, fallback to DOM presence: {e}")
                locator, resolved_selector = await self._resolve_locator(
                    selector,
                    action="wait_for_selector",
                    timeout=5000,
                    require_visible=False,
                    value=value,
                    step_description=step_description,
                )
                await locator.first.wait_for(timeout=5000, state="attached")
                logger.info(f"Fallback DOM presence wait succeeded for {selector}")
                return resolved_selector
            raise e

    async def hover(self, selector: str, **kwargs) -> str:
        """Hover an element."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        timeout = int(kwargs.pop("timeout", 10000))
        step_description = str(kwargs.pop("step_description", "") or "")
        locator, resolved_selector = await self._resolve_locator(
            selector,
            action="hover",
            timeout=timeout,
            require_visible=True,
            step_description=step_description,
        )
        await locator.hover(**kwargs)
        logger.debug(f"Hovered element: {selector}")
        return resolved_selector

    async def select(self, selector: str, value: str, **kwargs) -> str:
        """Select option in dropdown."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        timeout = int(kwargs.pop("timeout", 10000))
        step_description = str(kwargs.pop("step_description", "") or "")
        locator, resolved_selector = await self._resolve_locator(
            selector,
            action="select",
            timeout=timeout,
            require_visible=True,
            value=value,
            step_description=step_description,
        )
        await locator.select_option(value=value, **kwargs)
        logger.debug(f"Selected value '{value}' in {selector}")
        return resolved_selector

    async def press(self, selector: str, key: str, **kwargs) -> str:
        """Press keyboard key on element."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        timeout = int(kwargs.pop("timeout", 10000))
        step_description = str(kwargs.pop("step_description", "") or "")
        locator, resolved_selector = await self._resolve_locator(
            selector,
            action="press",
            timeout=timeout,
            require_visible=True,
            value=key,
            step_description=step_description,
        )
        await locator.press(key, **kwargs)
        logger.debug(f"Pressed key '{key}' on {selector}")
        return resolved_selector

    async def get_attribute(self, selector: str, name: str) -> Optional[str]:
        """Get attribute value of an element."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        locator = await self._get_preferred_locator(selector, timeout=10000, require_visible=False)
        value = await locator.get_attribute(name)
        logger.debug(f"Got attribute {name} from {selector}: {value}")
        return value
    
    async def screenshot(self, path: Optional[str] = None, **kwargs) -> bytes:
        """
        Take a screenshot.
        
        Args:
            path: Optional path to save screenshot
            **kwargs: Additional arguments for page.screenshot()
            
        Returns:
            Screenshot bytes
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        screenshot_bytes = await self.page.screenshot(path=path, **kwargs)
        logger.debug(f"Screenshot taken{f' and saved to {path}' if path else ''}")
        return screenshot_bytes

    def _parse_duration_to_ms(self, value: Any) -> int:
        """
        Parse duration from number/string and return milliseconds.
        Compatible with "2", "2s", "2000ms", "0.5s", "1000" (legacy ms).
        """
        if value is None:
            raise ValueError("Duration required")

        if isinstance(value, (int, float)):
            # Legacy compatibility: values >= 100 are likely ms, otherwise seconds.
            return int(value if value >= 100 else value * 1000)

        text = str(value).strip().lower()
        if not text:
            raise ValueError("Duration required")

        match = re.match(r"^\s*(\d+(?:\.\d+)?)\s*(ms|s)?\s*$", text)
        if not match:
            raise ValueError(f"Invalid wait duration: {value}")

        amount = float(match.group(1))
        unit = match.group(2)
        if unit == "ms":
            return int(amount)
        if unit == "s":
            return int(amount * 1000)
        return int(amount if amount >= 100 else amount * 1000)
    
    async def execute_action(self, action: str, selector: Optional[str] = None, 
                            value: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute a generic action based on action type.
        
        Args:
            action: Action type (goto, click, fill, wait, text_content, assert_text)
            selector: Element selector (for element actions)
            value: Value for the action (URL for goto, text for fill, etc.)
            **kwargs: Additional arguments
            
        Returns:
            Result dictionary with success status and optional output
        """
        result = {"success": False, "error": None, "output": None}
        
        try:
            call_kwargs = dict(kwargs)
            timeout_ms = call_kwargs.pop("timeout_ms", None)
            if timeout_ms is not None and "timeout" not in call_kwargs:
                call_kwargs["timeout"] = int(timeout_ms)

            if action == "goto":
                if not value:
                    raise ValueError("URL required for goto action")
                await self.goto(value, **call_kwargs)
            
            elif action == "wait":
                if not value:
                    raise ValueError("Duration required for wait action")
                ms = self._parse_duration_to_ms(value)
                await self.wait(ms)

            elif action == "wait_for_selector":
                if not selector:
                    raise ValueError("Selector required for wait_for_selector action")
                timeout = int(call_kwargs.get("timeout", 10000))
                state = call_kwargs.get("state", "visible")
                result["resolved_selector"] = await self.wait_for_selector(
                    selector,
                    timeout=timeout,
                    state=state,
                    step_description=str(call_kwargs.get("step_description", "") or ""),
                    value=value,
                )
            
            elif action == "click":
                if not selector:
                    raise ValueError("Selector required for click action")
                call_kwargs.pop("exact", None)
                call_kwargs.pop("state", None)
                result["resolved_selector"] = await self.click(selector, **call_kwargs)
            
            elif action == "fill":
                if not selector or not value:
                    raise ValueError("Selector and value required for fill action")
                call_kwargs.pop("exact", None)
                call_kwargs.pop("state", None)
                result["resolved_selector"] = await self.fill(selector, value, **call_kwargs)

            elif action == "select":
                if not selector or value is None:
                    raise ValueError("Selector and value required for select action")
                call_kwargs.pop("exact", None)
                call_kwargs.pop("state", None)
                result["resolved_selector"] = await self.select(selector, str(value), **call_kwargs)

            elif action == "hover":
                if not selector:
                    raise ValueError("Selector required for hover action")
                call_kwargs.pop("exact", None)
                call_kwargs.pop("state", None)
                result["resolved_selector"] = await self.hover(selector, **call_kwargs)

            elif action == "press":
                if not selector or not value:
                    raise ValueError("Selector and key required for press action")
                call_kwargs.pop("exact", None)
                call_kwargs.pop("state", None)
                result["resolved_selector"] = await self.press(selector, str(value), **call_kwargs)
            
            elif action == "text_content":
                if not selector:
                    raise ValueError("Selector required for text_content action")
                text = await self.get_text(selector)
                result["output"] = text

            elif action == "get_attribute":
                if not selector:
                    raise ValueError("Selector required for get_attribute action")
                attr_name = str(value or "value")
                result["output"] = await self.get_attribute(selector, attr_name)
            
            elif action == "assert_text":
                if not selector or not value:
                    raise ValueError("Selector and expected text required for assert_text action")
                exact = bool(call_kwargs.get("exact", False))
                if exact:
                    await self.assert_text(selector, str(value))
                else:
                    await self.assert_text_contains(selector, str(value))

            elif action == "assert_visible":
                if not selector:
                    raise ValueError("Selector required for assert_visible action")
                timeout = int(call_kwargs.get("timeout", 10000))
                result["resolved_selector"] = await self.assert_visible(
                    selector,
                    timeout=timeout,
                    step_description=str(call_kwargs.get("step_description", "") or ""),
                )

            elif action == "screenshot":
                result["output"] = await self.screenshot()
            
            else:
                raise ValueError(f"Unknown action: {action}")
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Action '{action}' failed: {e}")
        
        return result
