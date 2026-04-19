import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.agent_service import AgentService
from app.services.ai_service import AIService
from app.services.recorder import RecorderService


class FakeActionModel:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self):
        return self._payload


class FakeInteractedElement:
    def __init__(self, highlight_index, x_path):
        self.highlight_index = highlight_index
        self.x_path = x_path


class LocatorStabilityTests(unittest.IsolatedAsyncioTestCase):
    def test_agent_service_uses_matching_interacted_element_for_index(self):
        service = AgentService()
        action_model = FakeActionModel(
            {
                "click_element": {
                    "index": 7,
                }
            }
        )
        interacted_elements = [
            FakeInteractedElement(2, "//button[@id='wrong']"),
            FakeInteractedElement(7, "//button[@id='expected']"),
        ]

        step = service._action_to_platform_step(
            action_model,
            interacted_elements=interacted_elements,
        )

        self.assertIsNotNone(step)
        self.assertEqual(step["target"], "//button[@id='expected']")

    def test_bind_steps_to_library_matches_using_locator_chain(self):
        service = AIService()
        steps = [
            {
                "action": "click",
                "target": "button:nth-of-type(2)",
                "description": "点击登录按钮",
                "locator_chain": {
                    "primary": '[data-testid="login-btn"]',
                    "fallback_1": "text=登录",
                },
            }
        ]
        project_memory = {
            "page_object_library": [
                {
                    "page_id": 5,
                    "page_name": "Login",
                    "elements": [
                        {
                            "element_id": 9,
                            "name": "LoginButton",
                            "selector": '[data-testid="login-btn"]',
                            "type": "css",
                            "description": "登录按钮",
                        }
                    ],
                }
            ]
        }

        bound = service.bind_steps_to_library(steps, project_memory)

        self.assertEqual(bound[0]["element_id"], 9)
        self.assertEqual(bound[0]["page_id"], 5)
        self.assertEqual(bound[0]["target"], '[data-testid="login-btn"]')

    async def test_recorder_reinforcement_passes_db_and_updates_selector(self):
        service = RecorderService()
        service.page = SimpleNamespace(content=AsyncMock(return_value="<html></html>"))
        service.event_callback = AsyncMock()
        event = {
            "action": "click",
            "selector": "button",
            "metadata": {"innerText": "登录"},
        }

        class FakeSessionContext:
            async def __aenter__(self):
                return "db-session"

            async def __aexit__(self, exc_type, exc, tb):
                return False

        async def fake_heal_element(*, db, element_metadata, page_source, screenshot_description):
            self.assertEqual(db, "db-session")
            self.assertEqual(element_metadata, event["metadata"])
            self.assertEqual(page_source, "<html></html>")
            self.assertIn("click", screenshot_description)
            return {
                "locator_chain": {
                    "primary": '[data-testid="login-btn"]',
                },
                "confidence": 0.92,
            }

        with patch("app.services.recorder.AsyncSessionLocal", return_value=FakeSessionContext()):
            with patch("app.services.recorder.ai_service.heal_element", new=AsyncMock(side_effect=fake_heal_element)):
                await service._handle_event(None, event)

        self.assertTrue(event["ai_reinforced"])
        self.assertEqual(event["selector"], '[data-testid="login-btn"]')
        service.event_callback.assert_awaited_once()

