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
        """执行单个测试用例，带变量上下文支持"""
        result = {
            "success": False,
            "steps": [],
            "error": None,
            "screenshot": None,
            "context": {}  # 返回执行后的上下文快照
        }
        
        # 初始化变量上下文
        execution_context = {}
        
        # Fetch test case with module and project
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

        base_url = test_case.module.project.base_url if test_case.module and test_case.module.project else None

        # Initialize Allure Result
        test_uuid = str(uuid.uuid4())
        test_result = TestResult(uuid=test_uuid, name=test_case.name)
        test_result.fullName = f"TestCase_{test_case.id}_{test_case.name}"
        test_result.start = int(datetime.now().timestamp() * 1000)
        
        async with PlaywrightTool(headless=headless, browser_type=browser_type) as tool:
            try:
                if base_url:
                    await tool.goto(base_url)
                    await tool.wait(1000)
                
                for step_index, step in enumerate(test_case.steps):
                    step_start = int(datetime.now().timestamp() * 1000)
                    
                    # 注入执行上下文
                    step_result = await self._execute_step(tool, step, execution_context, step_index, test_case.id)
                    result["steps"].append(step_result)
                    
                    # 生成步骤报告
                    step_res_obj = TestStepResult(
                        name=f"[{step_index+1}] {step_result['action']} {step_result.get('resolved_value') or ''}", 
                        start=step_start,
                        stop=int(datetime.now().timestamp() * 1000)
                    )
                    
                    # 截图附件逻辑保持不变
                    try:
                        screenshot_bytes = await tool.screenshot()
                        attachment_uuid = str(uuid.uuid4())
                        with open(os.path.join(self.results_dir, f"{attachment_uuid}.png"), "wb") as f:
                            f.write(screenshot_bytes)
                        test_result.attachments.append(allure_commons.model2.Attachment(
                            name=f"Step {step_index+1}", source=f"{attachment_uuid}.png", type=AttachmentType.PNG
                        ))
                    except: pass
                    
                    if step_result["success"]:
                        step_res_obj.status = Status.PASSED
                    else:
                        step_res_obj.status = Status.FAILED
                        step_res_obj.statusDetails = StatusDetails(message=step_result.get("error"))
                        test_result.steps.append(step_res_obj)
                        raise Exception(f"Step {step_index+1} failed: {step_result.get('error')}")
                    
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
                    result["screenshot"] = base64.b64encode(screenshot_bytes).decode('utf-8')
                except: pass
            finally:
                test_result.stop = int(datetime.now().timestamp() * 1000)
                result["context"] = execution_context
                # 保存 Allure 结果
                with open(os.path.join(self.results_dir, f"{test_uuid}-result.json"), "w") as f:
                    import json, attr
                    from enum import Enum
                    class AllureEncoder(json.JSONEncoder):
                        def default(self, obj):
                            if isinstance(obj, Enum): return obj.value[0] if isinstance(obj.value, tuple) else obj.value
                            return super().default(obj)
                    json.dump(attr.asdict(test_result), f, cls=AllureEncoder, indent=4)
                
        return result

    def _resolve_variables(self, text: Any, context: Dict[str, Any]) -> Any:
        """解析字符串中的 {{var}} 占位符"""
        if not isinstance(text, str) or "{{" not in text:
            return text
        
        import re
        pattern = r"\{\{\s*(\w+)\s*\}\}"
        
        def replace(match):
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))
        
        return re.sub(pattern, replace, text)

    async def _execute_step(self, tool: PlaywrightTool, step: Dict[str, Any], context: Dict[str, Any], step_index: int, case_id: int) -> Dict[str, Any]:
        """执行单个步骤，支持变量解析与提取"""
        action_raw = step.get("action") or ""
        action = action_raw.strip().lower()
        
        # 1. 解析原始值中的变量
        raw_value = step.get("value")
        resolved_value = self._resolve_variables(raw_value, context)
        
        element_id = step.get("element_id")
        variable_name = step.get("variable_name")  # 步骤产出的变量名记录

        step_res = {
            "action": action,
            "success": False,
            "error": None,
            "resolved_value": resolved_value
        }

        logger.info(f"[Runner v6.0] Case {case_id} Step {step_index} Context: {context}")
        
        try:
            # ── A. Data Extraction Actions (New) ──────────────────────────
            if action in ["get_text", "extract_text", "提取文本"]:
                selector = await self._resolve_selector(step, element_id)
                res = await tool.get_text(selector)
                if res is not None:
                    # 如果步骤没定义 variable_name，默认用 step_{idx}_text
                    v_name = variable_name or f"step_{step_index}_text"
                    context[v_name] = res
                    step_res["success"] = True
                    step_res["output"] = res
                    logger.info(f"[Runner] Extracted text '{res}' into context['{v_name}']")
                return step_res

            if action in ["get_attribute", "extract_attr", "提取属性"]:
                selector = await self._resolve_selector(step, element_id)
                attr_name = resolved_value or "value"
                res = await tool.execute_action("get_attribute", selector, attr_name)
                if res["success"]:
                    v_name = variable_name or f"step_{step_index}_attr"
                    context[v_name] = res["output"]
                    step_res["success"] = True
                    step_res["output"] = res["output"]
                return step_res

            if action in ["set_variable", "设置变量"]:
                v_name = variable_name or step.get("key")
                if v_name:
                    context[v_name] = resolved_value
                    step_res["success"] = True
                return step_res

            # ── B. Standard Actions (with variable resolution) ──────────────
            if action in ["goto", "wait", "跳转", "访问", "打开", "等待"]:
                # goto 的目标通常也在 value 里
                result = await tool.execute_action(action=action, selector=None, value=resolved_value)
                step_res["success"] = result["success"]
                step_res["error"] = result.get("error")
                return step_res

            # ── C. Element Actions with Healing ──────────────────────────
            selector = await self._resolve_selector(step, element_id)
            selectors_to_try = [selector] if selector else []
            
            # TODO: 这里之后可以集成更复杂的定位链解析，目前先复用 primary
            
            result = await tool.execute_action(action=action, selector=selector, value=resolved_value)
            if result["success"]:
                step_res["success"] = True
                if result.get("output"): step_res["output"] = result["output"]
            else:
                step_res["error"] = result.get("error")

        except Exception as e:
            step_res["error"] = str(e)

        return step_res

    async def _resolve_selector(self, step: Dict[str, Any], element_id: int | None) -> str | None:
        """解析选择器（支持从数据库 Element 获取）"""
        primary_selector = step.get("target") or step.get("selector")
        if element_id:
            stmt = select(PageElement).where(PageElement.id == element_id)
            res = await self.db.execute(stmt)
            element = res.scalars().first()
            if element:
                return element.locator_value
        return primary_selector

    async def _write_heal_log(self, case_id: int | None, element_id: int | None, step_index: int, 
                             original_selector: str, healed_selector: str | None, 
                             heal_method: str, status: str) -> None:
        """Heal Log 相关逻辑保持不变"""
        try:
            from app.models.heal_log import HealLog
            log = HealLog(
                case_id=case_id, element_id=element_id, step_index=step_index,
                original_selector=original_selector, healed_selector=healed_selector,
                heal_method=heal_method, confidence=1.0 if healed_selector else 0.0,
                status=status
            )
            self.db.add(log)
            await self.db.commit()
        except: pass
