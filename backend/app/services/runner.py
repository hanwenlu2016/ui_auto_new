"""
测试用例执行器模块

本模块负责执行 UI 自动化测试用例：
1. 使用 Playwright 驱动浏览器执行测试步骤
2. 生成 Allure 格式的测试结果
3. 捕获每个步骤的截图作为附件
4. 处理测试执行过程中的异常

执行流程：
- 从数据库加载测试用例及其关联的页面元素
- 自动导航到项目的 base_url（如果配置）
- 逐步执行测试步骤
- 生成 JSON 格式的 Allure 测试结果
"""
import asyncio
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.case import TestCase
from app.models.element import PageElement
from app.tools.playwright_tool import PlaywrightTool
from app.services.ai_service import ai_service
import allure_commons
from allure_commons.types import LabelType, AttachmentType
from allure_commons.model2 import TestResult, TestStepResult, Status, StatusDetails, Label, Parameter

# 使用全局日志系统
from app.core.logger import logger

class TestRunner:
    """
    测试用例执行器类
    
    负责执行单个测试用例，生成 Allure 测试报告。
    """
    def __init__(self, db: AsyncSession, results_dir: str = None):
        """
        初始化测试执行器
        
        Args:
            db: 异步数据库会话
            results_dir: Allure 结果存储目录。如果未提供，使用默认的 backend/allure-results
        """
        self.db = db
        # 计算 Allure 结果目录路径（backend/allure-results）
        # runner.py 位于 backend/app/services/，需要向上3级
        if results_dir:
            self.results_dir = results_dir
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.results_dir = os.path.join(base_dir, "allure-results")
        
        os.makedirs(self.results_dir, exist_ok=True)

    async def run_test_case(self, test_case_id: int, headless: bool = True, browser_type: str = "chromium") -> Dict[str, Any]:
        """
        执行单个测试用例
        
        Args:
            test_case_id: 测试用例 ID
            headless: 是否使用无头模式运行浏览器
            browser_type: 浏览器类型 (chromium/firefox/webkit)
        
        Returns:
            Dict[str, Any]: 包含以下键的字典：
                - success (bool): 测试是否成功
                - steps (List): 每个步骤的执行结果
                - error (str): 错误信息（如果失败）
                - screenshot (str): Base64编码的失败截图（如果失败）
        """
        result = {
            "success": False,
            "steps": [],
            "error": None,
            "screenshot": None
        }
        
        # Fetch test case with module and project in one query using joinedload
        from sqlalchemy.orm import joinedload
        from app.models.module import Module
        from app.models.project import Project
        
        stmt = (
            select(TestCase)
            .options(joinedload(TestCase.module).joinedload(Module.project))
            .where(TestCase.id == test_case_id)
        )
        res = await self.db.execute(stmt)
        test_case = res.scalars().first()
        
        if not test_case:
            result["error"] = "Test case not found"
            return result

        # Get base_url from project through module relationship
        base_url = None
        if test_case.module and test_case.module.project:
            base_url = test_case.module.project.base_url

        # Initialize Allure Result
        test_uuid = str(uuid.uuid4())
        test_result = TestResult(uuid=test_uuid, name=test_case.name)
        test_result.fullName = f"TestCase_{test_case.id}_{test_case.name}"
        test_result.historyId = f"TestCase_{test_case.id}"
        test_result.testCaseId = str(test_case.id)
        test_result.start = int(datetime.now().timestamp() * 1000)
        test_result.labels.append(Label(name=LabelType.FEATURE, value="UI Automation"))
        test_result.labels.append(Label(name=LabelType.STORY, value=test_case.name))
        
        # Use PlaywrightTool for browser automation
        async with PlaywrightTool(headless=headless, browser_type=browser_type) as tool:
            try:
                # Auto-navigate to project base_url if available
                if base_url:
                    logger.info(f"Navigating to project base URL: {base_url}")
                    await tool.goto(base_url)
                    await tool.wait(1000)  # Wait for page to load
                
                for step_index, step in enumerate(test_case.steps):
                    step_start = int(datetime.now().timestamp() * 1000)
                    step_uuid = str(uuid.uuid4())
                    step_res_obj = TestStepResult(name=f"{step.get('action')} {step.get('value') or ''}", start=step_start)
                    
                    # Inject context for self-healing identification
                    step["_step_index"] = step_index
                    step["_case_id"] = test_case_id
                    
                    try:
                        step_result = await self._execute_step(tool, step)
                        result["steps"].append(step_result)
                        
                        # Capture screenshot after each step
                        try:
                            screenshot_bytes = await tool.screenshot()
                            attachment_uuid = str(uuid.uuid4())
                            screenshot_path = os.path.join(self.results_dir, f"{attachment_uuid}-step-{step_index+1}.png")
                            with open(screenshot_path, "wb") as f:
                                f.write(screenshot_bytes)
                            
                            test_result.attachments.append(allure_commons.model2.Attachment(
                                name=f"Step {step_index+1}: {step.get('action')}",
                                source=f"{attachment_uuid}-step-{step_index+1}.png",
                                type=AttachmentType.PNG
                            ))
                            logger.debug(f"Screenshot captured for step {step_index+1}")
                        except Exception as se:
                            logger.error(f"Failed to capture step screenshot: {se}")
                        
                        step_res_obj.stop = int(datetime.now().timestamp() * 1000)
                        if step_result["success"]:
                            step_res_obj.status = Status.PASSED
                        else:
                            step_res_obj.status = Status.FAILED
                            step_res_obj.statusDetails = StatusDetails(message=step_result.get("error"))
                            raise Exception(f"Step failed: {step_result.get('error')}")
                            
                    except Exception as e:
                        step_res_obj.stop = int(datetime.now().timestamp() * 1000)
                        step_res_obj.status = Status.BROKEN
                        step_res_obj.statusDetails = StatusDetails(message=str(e))
                        raise e
                    finally:
                        test_result.steps.append(step_res_obj)

                result["success"] = True
                test_result.status = Status.PASSED
                
            except Exception as e:
                result["error"] = str(e)
                test_result.status = Status.FAILED
                test_result.statusDetails = StatusDetails(message=str(e))
                
                try:
                    # Capture failure screenshot
                    import base64
                    screenshot_bytes = await tool.screenshot()
                    result["screenshot"] = base64.b64encode(screenshot_bytes).decode('utf-8')
                    
                    # Attach to Allure
                    attachment_uuid = str(uuid.uuid4())
                    with open(os.path.join(self.results_dir, f"{attachment_uuid}-attachment.png"), "wb") as f:
                        f.write(screenshot_bytes)
                    
                    test_result.attachments.append(allure_commons.model2.Attachment(
                        name="Screenshot",
                        source=f"{attachment_uuid}-attachment.png",
                        type=AttachmentType.PNG
                    ))
                    
                except Exception as se:
                    logger.error(f"Failed to take screenshot: {se}")
            finally:
                test_result.stop = int(datetime.now().timestamp() * 1000)
                
                # Write Allure Result
                with open(os.path.join(self.results_dir, f"{test_uuid}-result.json"), "w") as f:
                    import json
                    import attr
                    from enum import Enum
                    
                    class AllureEncoder(json.JSONEncoder):
                        def default(self, obj):
                            if isinstance(obj, Enum):
                                value = obj.value
                                if isinstance(value, tuple):
                                    return value[0]  # Return MIME type
                                return value
                            return super().default(obj)
                            
                    json.dump(attr.asdict(test_result), f, cls=AllureEncoder, indent=4)
                
        return result

    async def _execute_step(self, tool: PlaywrightTool, step: Dict[str, Any]) -> Dict[str, Any]:
        action_raw = step.get("action") or ""
        action = action_raw.strip().lower()
        value = step.get("value")
        element_id = step.get("element_id")
        step_index = step.get("_step_index", 0)   # injected by caller
        case_id = step.get("_case_id", None)       # injected by caller

        step_res = {
            "action": action,
            "success": False,
            "error": None
        }

        logger.info(f"[Runner V2.11] Case {case_id} Step {step_index} executing: action='{action}' (raw='{action_raw}'), value='{value}'")
        try:
            # ── 1. Handle Global Actions (No element needed) ────────────────
            if action in ["goto", "wait", "跳转", "访问", "打开", "等待"]:
                effective_value = value or (step.get("target") if action == "goto" else None)
                logger.info(f"[Runner] Global action detected: {action}, effective_value='{effective_value}'")
                result = await tool.execute_action(action=action, selector=None, value=effective_value)
                step_res["success"] = result["success"]
                step_res["error"] = result.get("error")
                return step_res

            # ── 2. Resolve primary selector for element actions ──────────────
            primary_selector = step.get("target") or step.get("selector")
            element = None

            if element_id:
                stmt = select(PageElement).where(PageElement.id == element_id)
                res = await self.db.execute(stmt)
                element = res.scalars().first()
                if element:
                    primary_selector = element.locator_value
                elif not primary_selector:
                    raise Exception(f"Element {element_id} not found")

            # ── 3. Build locator chain from step or element ───────────────────
            chain_dict = step.get("locator_chain") or {}
            if element and element.metadata_json:
                chain_dict = element.metadata_json.get("locator_chain") or chain_dict

            selectors_to_try: List[str] = []
            if primary_selector:
                selectors_to_try.append(primary_selector)
            for key in ("primary", "fallback_1", "fallback_2", "fallback_3"):
                val = chain_dict.get(key)
                if val and val not in selectors_to_try:
                    selectors_to_try.append(val)

            if not selectors_to_try:
                selectors_to_try = [primary_selector] if primary_selector else []

            # ── 4. Try selectors in priority order ──────────────────────────
            last_error: str = ""
            total_selectors = len(selectors_to_try)
            for attempt_idx, selector in enumerate(selectors_to_try):
                if not selector: continue
                
                # 如果不是最后一个候选选择器，设置 5s 短超时以实现快速故障转移 (Fail-Fast)
                action_kwargs = {}
                if attempt_idx < total_selectors - 1:
                    action_kwargs["timeout"] = 5000
                    
                try:
                    result = await tool.execute_action(action=action, selector=selector, value=value, **action_kwargs)
                    if result["success"]:
                        step_res["success"] = True
                        step_res["error"] = None
                        if result.get("output"): step_res["output"] = result["output"]

                        # Self-healing logic
                        if attempt_idx > 0:
                            await self._write_heal_log(
                                case_id=case_id, element_id=element_id, step_index=step_index,
                                original_selector=primary_selector or "", healed_selector=selector,
                                heal_method=f"fallback_{attempt_idx}", status="auto_healed"
                            )
                        break
                    else:
                        last_error = result.get("error") or "unknown"
                except Exception as exc:
                    last_error = str(exc)

            if not step_res["success"]:
                # ── 5. TRUE AI Dynamic Healing (Last Resort) ─────────────────
                logger.info(f"[Runner V2.13] All static selectors failed. Triggering True AI Dynamic Healing for Case {case_id} Step {step_index}")
                try:
                    page_source = await tool.get_text("html") or ""
                    # We might not have full metadata for an imaginary element, but we pass what we have
                    element_metadata = {
                        "action": action,
                        "intended_value": value,
                        "failed_selectors": selectors_to_try
                    }
                    
                    heal_result = await ai_service.heal_element(
                        element_metadata=element_metadata,
                        page_source=page_source,
                        screenshot_description=f"Action '{action}' failed on all known selectors"
                    )
                    
                    new_locator_chain = heal_result.get("locator_chain", {})
                    new_selectors = [new_locator_chain.get(k) for k in ["primary", "fallback_1", "fallback_2", "fallback_3"] if new_locator_chain.get(k)]
                    
                    dynamic_success = False
                    for ai_selector in new_selectors:
                        if not ai_selector: continue
                        logger.info(f"[Runner V2.13] Trying AI-Healed Dynamic Selector: {ai_selector}")
                        try:
                            result = await tool.execute_action(action=action, selector=ai_selector, value=value, timeout=10000)
                            if result["success"]:
                                step_res["success"] = True
                                step_res["error"] = None
                                if result.get("output"): step_res["output"] = result["output"]
                                
                                await self._write_heal_log(
                                    case_id=case_id, element_id=element_id, step_index=step_index,
                                    original_selector=primary_selector or "", healed_selector=ai_selector,
                                    heal_method="dynamic_ai_dom_healing", status="auto_healed"
                                )
                                dynamic_success = True
                                break
                            else:
                                last_error = result.get("error") or "dynamic ai selector failed"
                        except Exception as exc:
                            last_error = str(exc)
                            
                    if not dynamic_success:
                        if selectors_to_try:
                            await self._write_heal_log(
                                case_id=case_id, element_id=element_id, step_index=step_index,
                                original_selector=primary_selector or "", healed_selector=None,
                                heal_method="all_failed_including_ai", status="manual_review"
                            )
                        step_res["error"] = last_error or "All locator chain selectors exhausted including AI dynamic healing"
                except Exception as ai_exc:
                    logger.error(f"[Runner V2.13] True AI Healing failed: {ai_exc}", exc_info=True)
                    if selectors_to_try:
                        await self._write_heal_log(
                            case_id=case_id, element_id=element_id, step_index=step_index,
                            original_selector=primary_selector or "", healed_selector=None,
                            heal_method="all_failed", status="manual_review"
                        )
                    step_res["error"] = last_error or f"All locator chain selectors exhausted. Realtime AI heal also failed: {ai_exc}"

        except Exception as e:
            step_res["error"] = str(e)

        return step_res

    # ─── Heal Log Helper ──────────────────────────────────────────────────────

    async def _write_heal_log(
        self,
        case_id: int | None,
        element_id: int | None,
        step_index: int,
        original_selector: str,
        healed_selector: str | None,
        heal_method: str,
        status: str,
    ) -> None:
        """Persist a HealLog entry. Swallows exceptions so as not to interrupt runner flow."""
        try:
            from app.models.heal_log import HealLog
            log = HealLog(
                case_id=case_id,
                element_id=element_id,
                step_index=step_index,
                original_selector=original_selector,
                healed_selector=healed_selector,
                heal_method=heal_method,
                confidence=1.0 if healed_selector else 0.0,
                change_summary=f"Runner locator-chain attempt: {heal_method}",
                status=status,
            )
            self.db.add(log)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to write HealLog: {e}")
