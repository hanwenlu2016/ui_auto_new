import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api.v1.endpoints import ai as ai_endpoint
from app.services.agent_service import AgentService
from app.services.ai_service import AIService
from app.services.base import CRUDBase
from app.services.element_service import ElementService
from app.services.recorder import RecorderService
from app.services.runner import TestRunner
from app.models.element import PageElement
from app.schemas.element import PageElementCreate


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

    def test_bind_steps_to_library_matches_element_selector_aliases_from_metadata(self):
        service = AIService()
        steps = [
            {
                "action": "click",
                "target": "text=提交",
                "description": "点击提交按钮",
            }
        ]
        project_memory = {
            "page_object_library": [
                {
                    "page_id": 6,
                    "page_name": "Checkout",
                    "elements": [
                        {
                            "element_id": 12,
                            "name": "SubmitButton",
                            "selector": '[data-testid="submit-btn"]',
                            "type": "css",
                            "description": "提交按钮",
                            "metadata_json": {
                                "locator_chain": {
                                    "primary": '[data-testid="submit-btn"]',
                                    "fallback_1": "text=提交",
                                    "fallback_2": "button.primary",
                                }
                            },
                        }
                    ],
                }
            ]
        }

        bound = service.bind_steps_to_library(steps, project_memory)

        self.assertEqual(bound[0]["element_id"], 12)
        self.assertEqual(bound[0]["page_id"], 6)
        self.assertEqual(bound[0]["target"], '[data-testid="submit-btn"]')

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

    async def test_runner_uses_element_metadata_locator_candidates(self):
        element = SimpleNamespace(
            locator_value='[data-testid="submit-btn"]',
            metadata_json={
                "locator_chain": {
                    "primary": '[data-testid="submit-btn"]',
                    "fallback_1": 'text=提交',
                    "fallback_2": 'button.primary',
                },
                "selector_aliases": ['button[data-role="submit"]'],
            },
        )
        fake_scalar_result = SimpleNamespace(first=lambda: element)
        fake_execute_result = SimpleNamespace(scalars=lambda: fake_scalar_result)
        fake_db = SimpleNamespace(execute=AsyncMock(return_value=fake_execute_result))
        runner = TestRunner(db=fake_db)

        candidates = await runner._build_selector_candidates(
            step={"action": "click"},
            element_id=99,
            action="click",
        )

        self.assertEqual(
            candidates,
            [
                '[data-testid="submit-btn"]',
                'text=提交',
                'button.primary',
                'button[data-role="submit"]',
            ],
        )

    async def test_generate_endpoint_uses_project_memory_and_returns_steps(self):
        fake_db = object()
        current_user = SimpleNamespace(id=1)
        project_memory = {"feedbacks": [{"ai_notes": "Prefer stable selectors"}], "page_object_library": []}
        generated_steps = [
            {
                "action": "click",
                "target": '[data-testid="login-btn"]',
                "description": "点击登录按钮",
            }
        ]

        with patch(
            "app.api.v1.endpoints.ai.ai_service.load_project_memory",
            new=AsyncMock(return_value=project_memory),
        ) as load_project_memory:
            with patch(
                "app.api.v1.endpoints.ai.ai_service.generate_steps_from_text",
                new=AsyncMock(return_value=generated_steps),
            ) as generate_steps_from_text:
                response = await ai_endpoint.generate_steps(
                    db=fake_db,
                    request=ai_endpoint.GenerateRequest(
                        prompt="点击登录按钮",
                        project_id=8,
                        business_rules="Prefer data-testid",
                    ),
                    current_user=current_user,
                )

        self.assertEqual(response["steps"], generated_steps)
        load_project_memory.assert_awaited_once_with(fake_db, 8)
        generate_steps_from_text.assert_awaited_once_with(
            db=fake_db,
            prompt="点击登录按钮",
            business_rules="Prefer data-testid",
            project_memory=project_memory,
            model_id=None,
        )

    def test_clean_generated_steps_normalizes_action_aliases_and_waits(self):
        service = AIService()

        cleaned = service._clean_generated_steps(
            [
                {"action": "open", "target": "https://example.com"},
                {"action": "等待", "value": "2s"},
                {"action": "verify visible", "target": "#dashboard"},
            ]
        )

        self.assertEqual(cleaned[0]["action"], "goto")
        self.assertEqual(cleaned[0]["value"], "https://example.com")
        self.assertEqual(cleaned[0]["target"], "")
        self.assertEqual(cleaned[1]["action"], "wait")
        self.assertEqual(cleaned[1]["wait_ms"], 2000)
        self.assertEqual(cleaned[1]["value"], "2000")
        self.assertEqual(cleaned[2]["action"], "assert_visible")

    async def test_generate_endpoint_binds_steps_before_returning(self):
        fake_db = object()
        current_user = SimpleNamespace(id=1)
        project_memory = {
            "feedbacks": [],
            "page_object_library": [
                {
                    "page_id": 7,
                    "page_name": "Login",
                    "elements": [
                        {
                            "element_id": 3,
                            "name": "LoginButton",
                            "selector": '[data-testid="login-btn"]',
                            "type": "css",
                            "description": "登录按钮",
                        }
                    ],
                }
            ],
        }
        generated_steps = [
            {
                "action": "click",
                "target": '[data-testid="login-btn"]',
                "description": "点击登录按钮",
            }
        ]

        with patch(
            "app.api.v1.endpoints.ai.ai_service.load_project_memory",
            new=AsyncMock(return_value=project_memory),
        ):
            with patch(
                "app.api.v1.endpoints.ai.ai_service.generate_steps_from_text",
                new=AsyncMock(return_value=generated_steps),
            ):
                response = await ai_endpoint.generate_steps(
                    db=fake_db,
                    request=ai_endpoint.GenerateRequest(
                        prompt="点击登录按钮",
                        project_id=9,
                    ),
                    current_user=current_user,
                )

        self.assertEqual(response["steps"][0]["element_id"], 3)
        self.assertEqual(response["steps"][0]["page_id"], 7)
        self.assertEqual(response["steps"][0]["target"], '[data-testid="login-btn"]')

    async def test_element_service_create_merges_existing_element_by_selector_alias(self):
        service = ElementService(PageElement)
        existing = SimpleNamespace(
            id=4,
            name="SubmitButton",
            description="旧描述",
            locator_type="css",
            locator_value='[data-testid="submit-btn"]',
            metadata_json={
                "selector_aliases": ["text=提交"],
                "locator_chain": {"primary": '[data-testid="submit-btn"]'},
            },
        )
        fake_db = object()
        page_element_in = PageElementCreate(
            name="提交按钮",
            description="新描述",
            page_id=2,
            locator_type="css",
            locator_value="button.primary",
            metadata_json={
                "selector_aliases": ["button.primary"],
                "locator_chain": {
                    "primary": "button.primary",
                    "fallback_1": "text=提交",
                },
            },
        )

        with patch.object(ElementService, "get_multi", new=AsyncMock(return_value=[existing])):
            with patch.object(CRUDBase, "create", new=AsyncMock(return_value="created")) as base_create:
                with patch.object(CRUDBase, "update", new=AsyncMock(return_value="updated")) as base_update:
                    result = await service.create(
                        fake_db,
                        obj_in=page_element_in,
                        creator_id=1,
                        updater_id=1,
                    )

        self.assertEqual(result, "updated")
        base_create.assert_not_awaited()
        base_update.assert_awaited_once()
        update_kwargs = base_update.await_args.kwargs
        self.assertIs(update_kwargs["db_obj"], existing)
        self.assertEqual(update_kwargs["obj_in"]["locator_value"], "button.primary")
        self.assertEqual(update_kwargs["obj_in"]["description"], "旧描述")
        self.assertEqual(
            update_kwargs["obj_in"]["metadata_json"]["selector_aliases"],
            ['[data-testid="submit-btn"]', 'text=提交', 'button.primary'],
        )
