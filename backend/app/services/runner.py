import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.case import TestCase
from app.models.element import PageElement
from app.tools.playwright_tool import PlaywrightTool
import allure_commons
from allure_commons.types import LabelType, AttachmentType
from allure_commons.model2 import TestResult, TestStepResult, Status, StatusDetails, Label, Parameter

logger = logging.getLogger(__name__)

class TestRunner:
    def __init__(self, db: AsyncSession):
        self.db = db
        # Calculate paths relative to backend root directory
        # runner.py is in backend/app/services/
        # so we go up 3 levels to get backend/
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.results_dir = os.path.join(base_dir, "allure-results")
        os.makedirs(self.results_dir, exist_ok=True)

    async def run_test_case(self, test_case_id: int, headless: bool = True, browser_type: str = "chromium") -> Dict[str, Any]:
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
        action = step.get("action")
        value = step.get("value")
        element_id = step.get("element_id")
        
        step_res = {
            "action": action,
            "success": False,
            "error": None
        }
        
        try:
            # For actions that need element selector, fetch the element
            selector = None
            if element_id and action not in ["goto", "wait"]:
                stmt = select(PageElement).where(PageElement.id == element_id)
                res = await self.db.execute(stmt)
                element = res.scalars().first()
                
                if not element:
                    raise Exception(f"Element {element_id} not found")
                
                selector = element.locator_value
            
            # Execute action using PlaywrightTool
            result = await tool.execute_action(
                action=action,
                selector=selector,
                value=value
            )
            
            step_res["success"] = result["success"]
            step_res["error"] = result.get("error")
            if result.get("output"):
                step_res["output"] = result["output"]
                
        except Exception as e:
            step_res["error"] = str(e)
            
        return step_res
