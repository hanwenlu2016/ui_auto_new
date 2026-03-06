import asyncio
"""
测试录制服务模块

本模块负责录制用户在浏览器中的操作并生成测试用例：
1. 使用 Playwright 的 Inspector 模式录制用户操作
2. 捕获页面元素的定位器信息
3. 将录制的操作转换为测试步骤
4. 自动保存到数据库

录制模式：非无头模式，允许用户交互
"""
import json
from typing import Callable, Optional, List, Dict, Any
from playwright.async_api import async_playwright, Page, BrowserContext, Browser
from app.tools.playwright_tool import PlaywrightTool

# 使用全局日志系统
from app.core.logger import logger
from app.services.ai_service import ai_service

# Simple JS to capture events

RECORDER_SCRIPT = """
function getElementMetadata(el) {
    return {
        tagName: el.tagName,
        id: el.id || '',
        className: el.className || '',
        innerText: el.innerText ? el.innerText.substring(0, 100) : '',
        ariaLabel: el.getAttribute('aria-label') || '',
        placeholder: el.getAttribute('placeholder') || '',
        name: el.getAttribute('name') || '',
        outerHTML: el.outerHTML ? el.outerHTML.substring(0, 500) : ''
    };
}

document.addEventListener('click', (e) => {
    let target = e.target;
    if (target.tagName === 'INPUT' && (target.type === 'text' || target.type === 'password' || target.type === 'email')) {
        return;
    }

    let selector = '';
    if (target.id) {
        selector = '#' + target.id;
    } else if (target.className && typeof target.className === 'string' && target.className.trim() !== '') {
        selector = '.' + target.className.split(' ').filter(c => c.trim() !== '').join('.');
    } else {
        selector = target.tagName.toLowerCase();
    }
    
    // Simple XPath generator fallback
    if (!target.id) {
        let path = [];
        let el = target;
        while (el && el.nodeType === Node.ELEMENT_NODE) {
            let selector = el.nodeName.toLowerCase();
            if (el.id) {
                selector += '#' + el.id;
                path.unshift(selector);
                break;
            } else {
                let sib = el, nth = 1;
                while (sib = sib.previousElementSibling) {
                    if (sib.nodeName.toLowerCase() == selector)
                       nth++;
                }
                if (nth != 1)
                    selector += ":nth-of-type("+nth+")";
            }
            path.unshift(selector);
            el = el.parentNode;
        }
        selector = path.join(" > ");
    }

    window.recordEvent({
        action: 'click',
        selector: selector,
        value: '',
        metadata: getElementMetadata(target)
    });
}, true);

document.addEventListener('change', (e) => {
    let target = e.target;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') {
        let selector = '';
        if (target.id) {
            selector = '#' + target.id;
        } else {
             selector = target.tagName.toLowerCase(); 
        }
        
        window.recordEvent({
            action: 'fill',
            selector: selector,
            value: target.value,
            metadata: getElementMetadata(target)
        });
    }
}, true);
"""


class RecorderService:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.event_callback: Optional[Callable] = None

    async def start_recording(self, url: str, callback: Callable):
        self.event_callback = callback
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False) # Headful for user interaction
        self.context = await self.browser.new_context()
        
        # Expose function to receive events from browser
        await self.context.expose_binding("recordEvent", self._handle_event)
        
        self.page = await self.context.new_page()
        await self.page.add_init_script(RECORDER_SCRIPT)
        await self.page.goto(url)

    async def _handle_event(self, source, event):
        logger.info(f"Recorded event: {event}")
        
        # ─── AI Reinforcement (V3.0) ────────────────────────────────────────
        # If it's an interactive action, we reinforce it with AI locator_chain immediately
        if event.get("action") in ["click", "fill"] and self.page:
            try:
                logger.info(f"[Recorder V3.0] Reinforcing {event['action']} event with AI...")
                page_source = await self.page.content()
                
                # Call AI to generate a robust locator_chain based on pure metadata and current DOM
                heal_result = await ai_service.heal_element(
                    element_metadata=event.get("metadata", {}),
                    page_source=page_source,
                    screenshot_description=f"User performed {event['action']} during recording."
                )
                
                # Merge AI reinforcement results
                event["locator_chain"] = heal_result.get("locator_chain")
                event["ai_reinforced"] = True
                event["confidence"] = heal_result.get("confidence", 0.0)
                
                # If AI found a better primary selector than our basic JS guess, use it
                if event["locator_chain"] and event["locator_chain"].get("primary"):
                    event["selector"] = event["locator_chain"]["primary"]
                
                logger.info(f"[Recorder V3.0] AI reinforced successfully: {event['selector']}")
            except Exception as e:
                logger.error(f"[Recorder V3.0] AI reinforcement failed: {e}")
                event["ai_reinforced"] = False

        if self.event_callback:
            await self.event_callback(event)

    async def stop_recording(self):
        try:
            logger.info("Stopping recording and closing browser...")
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            logger.info("Recording stopped and browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing recording browser: {e}")
            
recorder_service = RecorderService()
