"""
Playwright automation tool for browser interactions.
Provides a clean interface for common browser automation tasks.
"""
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, expect

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
        await self.page.goto(url, **kwargs)
        logger.debug(f"Navigated to {url}")
    
    async def click(self, selector: str, **kwargs) -> None:
        """
        Click an element.
        
        Args:
            selector: CSS selector or XPath
            **kwargs: Additional arguments for locator.click()
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        locator = self.page.locator(selector)
        await locator.click(**kwargs)
        logger.debug(f"Clicked element: {selector}")
    
    async def fill(self, selector: str, value: str, **kwargs) -> None:
        """
        Fill an input field.
        
        Args:
            selector: CSS selector or XPath
            value: The value to fill
            **kwargs: Additional arguments for locator.fill()
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        locator = self.page.locator(selector)
        await locator.fill(value, **kwargs)
        logger.debug(f"Filled element {selector} with: {value}")
    
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
        locator = self.page.locator(selector)
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
        locator = self.page.locator(selector)
        await expect(locator).to_have_text(expected_text)
        logger.debug(f"Asserted text in {selector}: {expected_text}")
    
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
            if action == "goto":
                if not value:
                    raise ValueError("URL required for goto action")
                await self.goto(value, **kwargs)
            
            elif action == "wait":
                if not value:
                    raise ValueError("Duration required for wait action")
                # Convert seconds to milliseconds
                ms = int(float(value) * 1000)
                await self.wait(ms)
            
            elif action == "click":
                if not selector:
                    raise ValueError("Selector required for click action")
                await self.click(selector, **kwargs)
            
            elif action == "fill":
                if not selector or not value:
                    raise ValueError("Selector and value required for fill action")
                await self.fill(selector, value, **kwargs)
            
            elif action == "text_content":
                if not selector:
                    raise ValueError("Selector required for text_content action")
                text = await self.get_text(selector)
                result["output"] = text
            
            elif action == "assert_text":
                if not selector or not value:
                    raise ValueError("Selector and expected text required for assert_text action")
                await self.assert_text(selector, value)
            
            else:
                raise ValueError(f"Unknown action: {action}")
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Action '{action}' failed: {e}")
        
        return result
