"""
测试用例执行器模块

本模块负责执行 UI 自动化测试用例：
1. 使用 Playwright 驱动浏览器执行测试步骤
2. 生成 Allure 格式的测试结果
3. 捕获每个步骤的截图作为附件
4. 处理测试执行过程中的异常
"""
import os
import re
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

import allure_commons
from allure_commons.model2 import TestResult, TestStepResult, Status, StatusDetails
from allure_commons.types import AttachmentType

from app.core.logger import logger
from app.models.case import TestCase
from app.models.element import PageElement
from app.models.module import Module
from app.models.heal_log import HealLog
from app.tools.playwright_tool import PlaywrightTool
from app.services.ai_service import ai_service
from app.db.session import AsyncSessionLocal


class TestRunner:
    """测试用例执行器类。"""

    ELEMENT_ACTIONS = {
        "click",
        "fill",
        "select",
        "hover",
        "press",
        "assert_text",
        "assert_visible",
        "wait_for_selector",
        "get_text",
        "get_attribute",
    }

    INTERACTIVE_ACTIONS = {"click", "fill", "select", "hover", "press"}

    ACTION_ALIASES = {
        "open": "goto",
        "visit": "goto",
        "navigate": "goto",
        "跳转": "goto",
        "访问": "goto",
        "打开": "goto",
        "sleep": "wait",
        "等待": "wait",
        "text_content": "get_text",
        "extract_text": "get_text",
        "提取文本": "get_text",
        "extract_attr": "get_attribute",
        "提取属性": "get_attribute",
        "设置变量": "set_variable",
        "verify_text": "assert_text",
        "check_text": "assert_text",
        "verify_visible": "assert_visible",
        "check_visible": "assert_visible",
    }

    def __init__(self, db: AsyncSession, results_dir: Optional[str] = None):
        self.db = db
        if results_dir:
            self.results_dir = results_dir
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.results_dir = os.path.join(base_dir, "allure-results")
        os.makedirs(self.results_dir, exist_ok=True)

    async def run_test_case(
        self,
        test_case_id: int,
        headless: bool = True,
        browser_type: str = "chromium",
        executor_id: int = None,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "success": False,
            "steps": [],
            "error": None,
            "screenshot": None,
            "context": {},
        }
        execution_context: Dict[str, Any] = {}

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

        base_url = test_case.module.project.base_url if test_case.module and test_case.module.project else None

        test_uuid = str(uuid.uuid4())
        test_result = TestResult(uuid=test_uuid, name=test_case.name)
        test_result.fullName = f"TestCase_{test_case.id}_{test_case.name}"
        test_result.start = int(datetime.now().timestamp() * 1000)
        
        if executor_id:
             test_result.labels.append(allure_commons.model2.Label(name="executor", value=str(executor_id)))

        async with PlaywrightTool(headless=headless, browser_type=browser_type) as tool:
            try:
                if base_url:
                    await tool.goto(base_url)
                    await tool.wait(800)

                for step_index, raw_step in enumerate(test_case.steps or []):
                    step_start = int(datetime.now().timestamp() * 1000)
                    normalized_step = self._normalize_step(raw_step)
                    
                    # Create Allure step
                    step_title = f"[{step_index + 1}] {normalized_step['action']} {normalized_step.get('value') or ''}"
                    
                    step_res_obj = TestStepResult(
                        name=step_title,
                        start=step_start,
                        stop=step_start, # Will update later
                        status=Status.BROKEN # Default
                    )

                    try:
                        step_result = await self._execute_step(
                            tool=tool,
                            step=normalized_step,
                            context=execution_context,
                            step_index=step_index,
                            case_id=test_case.id,
                        )
                        result["steps"].append(step_result)

                        # Take screenshot immediately after step
                        try:
                            screenshot_bytes = await tool.screenshot()
                            attachment_uuid = str(uuid.uuid4())
                            with open(os.path.join(self.results_dir, f"{attachment_uuid}.png"), "wb") as f:
                                f.write(screenshot_bytes)
                            
                            # Add attachment to the STEP result
                            step_res_obj.attachments.append(
                                allure_commons.model2.Attachment(
                                    name="Screenshot",
                                    source=f"{attachment_uuid}.png",
                                    type=AttachmentType.PNG,
                                )
                            )
                        except Exception:
                            pass

                        if step_result["success"]:
                            step_res_obj.status = Status.PASSED
                        else:
                            step_res_obj.status = Status.FAILED
                            step_res_obj.statusDetails = StatusDetails(message=step_result.get("error"))
                            test_result.steps.append(step_res_obj)
                            raise Exception(f"Step {step_index + 1} failed: {step_result.get('error')}")

                    except Exception as e:
                        step_res_obj.status = Status.FAILED
                        step_res_obj.statusDetails = StatusDetails(message=str(e))
                        # If screenshot wasn't taken in try block (e.g. error in execute_step), take it here
                        if not step_res_obj.attachments:
                             try:
                                screenshot_bytes = await tool.screenshot()
                                attachment_uuid = str(uuid.uuid4())
                                with open(os.path.join(self.results_dir, f"{attachment_uuid}.png"), "wb") as f:
                                    f.write(screenshot_bytes)
                                step_res_obj.attachments.append(
                                    allure_commons.model2.Attachment(
                                        name="Error Screenshot",
                                        source=f"{attachment_uuid}.png",
                                        type=AttachmentType.PNG,
                                    )
                                )
                             except:
                                 pass
                        test_result.steps.append(step_res_obj)
                        raise e
                    
                    step_res_obj.stop = int(datetime.now().timestamp() * 1000)
                    test_result.steps.append(step_res_obj)

                result["success"] = True
                test_result.status = Status.PASSED
            except Exception as e:
                result["error"] = str(e)
                test_result.status = Status.FAILED
                test_result.statusDetails = StatusDetails(message=str(e))
                try:
                    import base64
                    screenshot_bytes = await tool.screenshot()
                    result["screenshot"] = base64.b64encode(screenshot_bytes).decode("utf-8")
                except Exception:
                    pass
            finally:
                test_result.stop = int(datetime.now().timestamp() * 1000)
                result["context"] = execution_context
                with open(os.path.join(self.results_dir, f"{test_uuid}-result.json"), "w") as f:
                    import attr
                    import json
                    from enum import Enum

                    class AllureEncoder(json.JSONEncoder):
                        def default(self, obj):
                            if isinstance(obj, Enum):
                                return obj.value[0] if isinstance(obj.value, tuple) else obj.value
                            return super().default(obj)

                    json.dump(attr.asdict(test_result), f, cls=AllureEncoder, indent=4)

        # Sanitize result for JSON serialization (Celery results)
        return self._to_json_safe(result)

    def _to_json_safe(self, obj: Any) -> Any:
        """
        Recursively convert non-serializable objects to JSON-safe primitives.
        Handles: Enum, Exception, UUID, datetime, bytes (base64 encoded), and general 'Error' objects.
        """
        import uuid
        from datetime import datetime
        from enum import Enum
        import base64

        if isinstance(obj, dict):
            return {str(k): self._to_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._to_json_safe(i) for i in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, Enum):
            return obj.value[0] if isinstance(obj.value, (list, tuple)) else obj.value
        elif isinstance(obj, (uuid.UUID, datetime)):
            return str(obj)
        elif isinstance(obj, bytes):
            try:
                return base64.b64encode(obj).decode("utf-8")
            except:
                return "<binary data>"
        elif isinstance(obj, Exception):
            return str(obj)
        elif hasattr(obj, "__class__") and obj.__class__.__name__ == "Error":
            # Specifically handle objects named 'Error' from libraries
            return str(obj)
        else:
            try:
                # If it's a Pydantic model (though not likely here)
                if hasattr(obj, "dict"):
                    return self._to_json_safe(obj.dict())
                if hasattr(obj, "model_dump"):
                    return self._to_json_safe(obj.model_dump())
                # Fallback to string representation for anything else unknown
                return str(obj)
            except:
                return f"<unserializable {type(obj).__name__}>"

    def _canonical_action(self, action: Any) -> str:
        raw = str(action or "").strip().lower()
        return self.ACTION_ALIASES.get(raw, raw)

    def _parse_wait_to_ms(self, value: Any, wait_ms: Any = None) -> Optional[int]:
        if wait_ms is not None:
            value = wait_ms
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value if value >= 100 else value * 1000)

        text = str(value).strip().lower()
        if not text:
            return None
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

    def _resolve_variables(self, text: Any, context: Dict[str, Any]) -> Any:
        if not isinstance(text, str) or "{{" not in text:
            return text

        pattern = r"\{\{\s*(\w+)\s*\}\}"

        def replace(match):
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))

        return re.sub(pattern, replace, text)

    def _normalize_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        action = self._canonical_action(step.get("action"))
        target = step.get("target") or step.get("selector")
        value = step.get("value")
        wait_ms = self._parse_wait_to_ms(value=value, wait_ms=step.get("wait_ms"))

        if action == "wait" and wait_ms is not None:
            value = str(wait_ms)
        if action == "goto" and not value and target:
            value = target
            target = ""

        return {
            "action": action,
            "target": target,
            "selector": target,
            "value": value,
            "wait_ms": wait_ms,
            "description": step.get("description") or "",
            "element_id": step.get("element_id"),
            "variable_name": step.get("variable_name"),
            "key": step.get("key"),
            "locator_chain": step.get("locator_chain"),
        }

    async def _execute_step(
        self,
        tool: PlaywrightTool,
        step: Dict[str, Any],
        context: Dict[str, Any],
        step_index: int,
        case_id: int,
    ) -> Dict[str, Any]:
        action = step.get("action")
        resolved_value = self._resolve_variables(step.get("value"), context)
        element_id = step.get("element_id")
        variable_name = step.get("variable_name")

        step_res: Dict[str, Any] = {
            "action": action,
            "success": False,
            "error": None,
            "resolved_value": resolved_value,
        }

        logger.info(f"[Runner v7.0] Case {case_id} Step {step_index} Action={action} Context={context}")

        try:
            if action == "set_variable":
                v_name = variable_name or step.get("key")
                if not v_name:
                    step_res["error"] = "set_variable requires variable_name or key"
                    return step_res
                context[v_name] = resolved_value
                step_res["success"] = True
                return step_res

            if action in {"goto", "wait", "screenshot"}:
                if action == "wait":
                    wait_ms = step.get("wait_ms") or self._parse_wait_to_ms(resolved_value)
                    if wait_ms is None:
                        step_res["error"] = f"Invalid wait value: {resolved_value}"
                        return step_res
                    resolved_value = str(wait_ms)
                    step_res["resolved_value"] = resolved_value
                result = await tool.execute_action(action=action, selector=None, value=resolved_value)
                step_res["success"] = result["success"]
                step_res["error"] = result.get("error")
                if result.get("output") is not None:
                    step_res["output"] = result.get("output")
                return step_res

            # Check for AI_AUTO instruction for direct PageAgent execution
            target = step.get("target") or step.get("selector")
            if target == "AI_AUTO" and action in self.INTERACTIVE_ACTIONS:
                agent_res = await self._execute_via_page_agent(tool, action, resolved_value, step)
                step_res["success"] = agent_res["success"]
                step_res["error"] = agent_res.get("error")
                if agent_res.get("output") is not None:
                    step_res["output"] = agent_res.get("output")
                if agent_res.get("used_selector"):
                    step_res["used_selector"] = agent_res["used_selector"]
                return step_res

            selectors = await self._build_selector_candidates(step, element_id, action)
            if action in self.ELEMENT_ACTIONS and not selectors:
                step_res["error"] = f"Action '{action}' requires selector, but none was resolved"
                return step_res

            if action == "get_text":
                res = await self._try_selectors(tool, action, selectors, resolved_value, step, case_id, step_index, element_id)
                if res["success"] and res.get("output") is not None:
                    v_name = variable_name or f"step_{step_index}_text"
                    context[v_name] = res["output"]
                    step_res["output"] = res["output"]
                step_res["success"] = res["success"]
                step_res["error"] = res.get("error")
                return step_res

            if action == "get_attribute":
                attr_name = resolved_value or "value"
                res = await self._try_selectors(tool, action, selectors, attr_name, step, case_id, step_index, element_id)
                if res["success"]:
                    v_name = variable_name or f"step_{step_index}_attr"
                    context[v_name] = res.get("output")
                    step_res["output"] = res.get("output")
                step_res["success"] = res["success"]
                step_res["error"] = res.get("error")
                return step_res

            if action in self.ELEMENT_ACTIONS:
                res = await self._try_selectors(tool, action, selectors, resolved_value, step, case_id, step_index, element_id)
                step_res["success"] = res["success"]
                step_res["error"] = res.get("error")
                if res.get("output") is not None:
                    step_res["output"] = res.get("output")
                if res.get("used_selector"):
                    step_res["used_selector"] = res["used_selector"]
                if res.get("tried_selectors"):
                    step_res["tried_selectors"] = res["tried_selectors"]
                return step_res

            step_res["error"] = f"Unknown action after normalization: {action}"
        except Exception as e:
            step_res["error"] = str(e)

        return step_res

    # _build_visible_selector_variants removed. We now trust extracted locators directly.

    async def _build_selector_candidates(
        self,
        step: Dict[str, Any],
        element_id: Optional[int],
        action: str,
    ) -> List[str]:
        candidates: List[str] = []

        # 1. Page Object Library Match (Highest Priority)
        if element_id:
            stmt = select(PageElement).where(PageElement.id == element_id)
            res = await self.db.execute(stmt)
            element = res.scalars().first()
            if element and element.locator_value:
                candidates.append(str(element.locator_value))

        # 2. Rich Locator Chain (Semantic, Text, Clean CSS, original XPath)
        locator_chain = step.get("locator_chain")
        if isinstance(locator_chain, dict):
            # Order of preference: Primary (Semantic) > Fallback 1 (Text) > Fallback 2 (Clean CSS) > Fallback 3 (XPath)
            ordered = [
                locator_chain.get("primary"),
                locator_chain.get("fallback_1"),
                locator_chain.get("fallback_2"),
                locator_chain.get("fallback_3"),
            ]
            candidates.extend([str(s) for s in ordered if s])
        elif isinstance(locator_chain, list):
            candidates.extend([str(s) for s in locator_chain if s])

        # 3. Raw Target (Original extraction from browser-use)
        primary_selector = step.get("target") or step.get("selector")
        if primary_selector and primary_selector != "AI_AUTO":
            candidates.append(str(primary_selector))

        # 4. Image-based Fallback (Experimental)
        if isinstance(locator_chain, dict) and locator_chain.get("fallback_image"):
            candidates.append(str(locator_chain["fallback_image"]))

        # deduplicate while preserving order
        seen = set()
        unique_candidates = []
        for selector in candidates:
            if selector and selector not in seen:
                seen.add(selector)
                unique_candidates.append(selector)
        return unique_candidates

    async def _execute_via_page_agent(
        self,
        tool: PlaywrightTool,
        action: str,
        value: Any,
        step: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Attempts to use PageAgent (client-side AI agent) to perform the action.
        Used for both direct execution (AI_AUTO) and fallback healing.
        """
        try:
            logger.info(f"[PageAgent Execution] Action={action} Target={step.get('target')} Desc={step.get('description')}")
            
            # 1. Check if PageAgent is available in the page
            is_available = await tool.page.evaluate("() => typeof window.pageAgent !== 'undefined'")
            if not is_available:
                # Inject it if missing (similar to recorder)
                import os
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                page_agent_path = os.path.join(base_dir, "app", "core", "static", "js", "page-agent.js")
                init_agent_path = os.path.join(base_dir, "app", "core", "static", "js", "init-agent.js")
                
                if os.path.exists(page_agent_path):
                    await tool.page.add_script_tag(path=page_agent_path)
                    if os.path.exists(init_agent_path):
                        await tool.page.add_script_tag(path=init_agent_path)
                    
                    # Wait for init
                    await tool.page.wait_for_function("() => typeof window.pageAgent !== 'undefined'", timeout=5000)
                else:
                    return {"success": False, "error": "PageAgent script not found"}

            # 2. Construct natural language prompt
            prompt = step.get("description")
            if not prompt:
                target = step.get("target") or step.get("selector")
                page_url = ""
                try:
                    page_url = tool.page.url if tool.page else ""
                except Exception:
                    pass

                if target == "AI_AUTO":
                    # Build a more actionable prompt from context instead of the useless "Perform click"
                    loc = f" on page '{page_url}'" if page_url else ""
                    if action == "click":
                        prompt = f"Click the most appropriate button or interactive element{loc}"
                        if value:
                            prompt += f" related to '{value}'"
                    elif action == "fill":
                        prompt = f"Find the most appropriate input field{loc} and type '{value}'"
                    elif action == "select":
                        prompt = f"Select the option '{value}' from the most appropriate dropdown{loc}"
                    elif action == "hover":
                        prompt = f"Hover over the most relevant element{loc}"
                        if value:
                            prompt += f" related to '{value}'"
                    elif action == "press":
                        prompt = f"Press the key '{value}' on the focused element{loc}"
                    else:
                        prompt = f"Perform {action}{loc}"
                        if value:
                            prompt += f" with value '{value}'"
                else:
                    if action == "click":
                        prompt = f"Click on the element that looks like {target}"
                    elif action == "fill":
                        prompt = f"Type '{value}' into the input field for {target}"
                    else:
                        prompt = f"Perform {action} on {target}"
            
            logger.info(f"[PageAgent Execution] Prompt: {prompt}")

            # 3. Register LLM proxy route — only once per browser context to prevent handler accumulation.
            # Playwright stacks route handlers on every .route() call; duplicate registration causes
            # exponential LLM requests and silent abort errors on the stale handlers.
            if not getattr(tool, "_llm_route_registered", False):
                async def _handle_llm_route(route):
                    try:
                        request = route.request
                        if request.method != "POST":
                            await route.continue_()
                            return
                        post_data = request.post_data_json
                        if not post_data:
                            await route.continue_()
                            return
                        
                        messages = post_data.get("messages", [])
                        async with AsyncSessionLocal() as db:
                            response_data = await ai_service.chat_completion(
                                db=db,
                                messages=messages,
                                temperature=post_data.get("temperature", 0.7),
                            )
                        
                        content = response_data.get("content", "") if isinstance(response_data, dict) else response_data
                        mock_response = {
                            "id": "chatcmpl-page-agent-proxy",
                            "object": "chat.completion",
                            "created": 1677652288,
                            "model": "gpt-3.5-turbo",
                            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}]
                        }
                        await route.fulfill(status=200, content_type="application/json", body=json.dumps(mock_response))
                    except Exception as e:
                        logger.error(f"LLM Route Error: {e}")
                        await route.abort()

                await tool.page.context.route("**/v1/chat/completions", _handle_llm_route)
                tool._llm_route_registered = True
                logger.info("[PageAgent] LLM proxy route registered on context")

            # 4. Execute via PageAgent with explicit timeout guard.
            # LLM reasoning can take 30-120s; without a timeout the evaluate call may
            # silently fail with a cryptic Playwright timeout after 30s.
            PAGE_AGENT_TIMEOUT_MS = 110000  # slightly under asyncio guard
            PAGE_AGENT_ASYNCIO_TIMEOUT_S = 120.0

            # Escape prompt for safe JS string interpolation
            safe_prompt = prompt.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
            js_code = f"""
            (async () => {{
                const _timeout = new Promise((_, reject) =>
                    setTimeout(() => reject(new Error('PageAgent timeout after {PAGE_AGENT_TIMEOUT_MS}ms')), {PAGE_AGENT_TIMEOUT_MS})
                );
                try {{
                    if (!window.pageAgent) throw new Error("PageAgent not initialized");
                    const result = await Promise.race([
                        window.pageAgent.execute("{safe_prompt}"),
                        _timeout
                    ]);
                    return {{ success: true, result: result }};
                }} catch (e) {{
                    return {{ success: false, error: e.toString() }};
                }}
            }})()
            """
            
            import asyncio
            try:
                result = await asyncio.wait_for(
                    tool.page.evaluate(js_code),
                    timeout=PAGE_AGENT_ASYNCIO_TIMEOUT_S,
                )
            except asyncio.TimeoutError:
                return {"success": False, "error": f"PageAgent asyncio timeout after {PAGE_AGENT_ASYNCIO_TIMEOUT_S}s"}
            
            if result.get("success"):
                return {"success": True, "output": result.get("result"), "used_selector": "PageAgent_AI"}
            else:
                return {"success": False, "error": f"PageAgent execution failed: {result.get('error')}"}

        except Exception as e:
            return {"success": False, "error": f"PageAgent execution exception: {str(e)}"}

    async def _try_selectors(
        self,
        tool: PlaywrightTool,
        action: str,
        selectors: List[str],
        value: Any,
        step: Dict[str, Any],
        case_id: int,
        step_index: int,
        element_id: Optional[int],
    ) -> Dict[str, Any]:
        
        tried_selectors: List[str] = []
        last_error: Optional[str] = None

        for idx, selector in enumerate(selectors):
            tried_selectors.append(selector)
            try:
                res = await tool.execute_action(action=action, selector=selector, value=value)
                if res["success"]:
                    return {
                        "success": True,
                        "used_selector": selector,
                        "tried_selectors": tried_selectors,
                        "output": res.get("output"),
                        "error": None
                    }
                else:
                    last_error = res.get("error")
            except Exception as e:
                last_error = str(e)
        
        # If all selectors failed, try PageAgent fallback
        if action in self.INTERACTIVE_ACTIONS:
            fallback_res = await self._execute_via_page_agent(tool, action, value, step)
            if fallback_res["success"]:
                 await self._write_heal_log(
                    case_id=case_id,
                    element_id=element_id,
                    step_index=step_index,
                    original_selector=selectors[0] if selectors else "unknown",
                    healed_selector="PageAgent_AI",
                    heal_method="page_agent_fallback",
                    status="auto_healed",
                )
                 return {
                    "success": True,
                    "used_selector": "PageAgent_AI",
                    "tried_selectors": tried_selectors,
                    "output": fallback_res.get("output"),
                }
            else:
                # Append fallback error to last error
                last_error = f"{last_error} | PageAgent Fallback: {fallback_res.get('error')}"

        return {
            "success": False,
            "used_selector": None,
            "tried_selectors": tried_selectors,
            "error": f"Action={action}; tried_selectors={tried_selectors}; final_error={last_error}",
        }


    async def _write_heal_log(
        self,
        case_id: Optional[int],
        element_id: Optional[int],
        step_index: int,
        original_selector: str,
        healed_selector: Optional[str],
        heal_method: str,
        status: str,
    ) -> None:
        try:
            log = HealLog(
                case_id=case_id,
                element_id=element_id,
                step_index=step_index,
                original_selector=original_selector,
                healed_selector=healed_selector,
                heal_method=heal_method,
                confidence=1.0 if healed_selector else 0.0,
                status=status,
            )
            self.db.add(log)
            await self.db.commit()
        except Exception as e:
            logger.warning(f"[HealLog] Failed to persist heal log (case={case_id}, step={step_index}): {e}")
