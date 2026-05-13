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

    def test_extract_steps_from_history_keeps_distinct_ai_auto_actions(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(
                        action=[
                            FakeActionModel({"click_element": {"index": 1}}),
                            FakeActionModel({"click_element": {"index": 2}}),
                            FakeActionModel({"input_text": {"index": 3, "text": "admin"}}),
                        ]
                    ),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                )
            ]
        )

        steps = service._extract_steps_from_history(history)

        self.assertEqual(len(steps), 3)
        self.assertEqual([step["action"] for step in steps], ["click", "click", "fill"])
        self.assertTrue(all(step["target"] == "AI_AUTO" for step in steps))
        self.assertEqual(steps[2]["value"], "admin")

    def test_build_step_identity_distinguishes_different_ai_auto_actions(self):
        service = AgentService()
        first_action = FakeActionModel({"click_element": {"index": 1}})
        second_action = FakeActionModel({"click_element": {"index": 2}})
        first_step = service._action_to_platform_step(first_action)
        second_step = service._action_to_platform_step(second_action)

        self.assertIsNotNone(first_step)
        self.assertIsNotNone(second_step)
        self.assertNotEqual(
            service._build_step_identity(first_step, first_action),
            service._build_step_identity(second_step, second_action),
        )

    def test_build_step_identity_dedupes_exact_same_ai_auto_action(self):
        service = AgentService()
        action = FakeActionModel({"click_element": {"index": 1}})
        step = service._action_to_platform_step(action)

        self.assertIsNotNone(step)
        self.assertEqual(
            service._build_step_identity(step, action),
            service._build_step_identity(step, action),
        )

    def test_build_step_identity_ignores_thought_for_ai_auto_action(self):
        service = AgentService()
        first_action = FakeActionModel({"thought": "先观察", "click_element": {"index": 1}})
        second_action = FakeActionModel({"thought": "直接点击", "click_element": {"index": 1}})
        step = service._action_to_platform_step(first_action)

        self.assertIsNotNone(step)
        self.assertEqual(
            service._build_step_identity(step, first_action),
            service._build_step_identity(step, second_action),
        )

    def test_build_step_identity_keeps_non_ai_auto_shape(self):
        service = AgentService()

        self.assertEqual(
            service._build_step_identity({"action": "click", "target": "#submit", "value": ""}),
            ("click", "#submit", ""),
        )

    def test_extract_steps_from_history_skips_only_exact_consecutive_duplicates(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(
                        action=[
                            FakeActionModel({"click_element": {"index": 1}}),
                            FakeActionModel({"click_element": {"index": 1}}),
                            FakeActionModel({"click_element": {"index": 2}}),
                        ]
                    ),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                )
            ]
        )

        steps = service._extract_steps_from_history(history)

        self.assertEqual(len(steps), 2)
        self.assertTrue(all(step["target"] == "AI_AUTO" for step in steps))

    def test_build_step_identity_falls_back_to_description_without_action_model(self):
        service = AgentService()
        step = {
            "action": "click",
            "target": "AI_AUTO",
            "value": "",
            "description": "点击右上角登录按钮",
        }

        self.assertEqual(
            service._build_step_identity(step),
            ("click", "AI_AUTO", "", "点击右上角登录按钮"),
        )

    def test_extract_steps_from_history_preserves_order(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(
                        action=[
                            FakeActionModel({"go_to_url": {"url": "https://example.com"}}),
                            FakeActionModel({"click_element": {"index": 1}}),
                            FakeActionModel({"input_text": {"index": 2, "text": "abc"}}),
                        ]
                    ),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                )
            ]
        )

        steps = service._extract_steps_from_history(history)

        self.assertEqual([step["action"] for step in steps], ["goto", "click", "fill"])
        self.assertEqual(steps[0]["value"], "https://example.com")
        self.assertEqual(steps[2]["value"], "abc")

    def test_extract_steps_from_history_keeps_same_ai_auto_fill_actions_with_same_text(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(
                        action=[
                            FakeActionModel({"input_text": {"index": 1, "text": "admin"}}),
                            FakeActionModel({"input_text": {"index": 2, "text": "admin"}}),
                        ]
                    ),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                )
            ]
        )

        steps = service._extract_steps_from_history(history)

        self.assertEqual(len(steps), 2)
        self.assertEqual([step["value"] for step in steps], ["admin", "admin"])

    def test_build_step_identity_handles_unserializable_action_model(self):
        service = AgentService()

        class BadActionModel:
            def model_dump(self):
                raise RuntimeError("boom")

        step = {
            "action": "click",
            "target": "AI_AUTO",
            "value": "",
            "description": "点击登录",
        }

        self.assertEqual(
            service._build_step_identity(step, BadActionModel()),
            ("click", "AI_AUTO", "", "点击登录"),
        )

    def test_extract_steps_from_history_dedupes_identical_non_ai_auto_steps(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(
                        action=[
                            FakeActionModel({"go_to_url": {"url": "https://example.com"}}),
                            FakeActionModel({"go_to_url": {"url": "https://example.com"}}),
                        ]
                    ),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                )
            ]
        )

        steps = service._extract_steps_from_history(history)

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["action"], "goto")
        self.assertEqual(steps[0]["value"], "https://example.com")

    def test_extract_steps_from_history_keeps_same_ai_auto_action_across_items(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(action=[FakeActionModel({"click_element": {"index": 1}})]),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                ),
                SimpleNamespace(
                    model_output=SimpleNamespace(action=[FakeActionModel({"click_element": {"index": 2}})]),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                ),
            ]
        )

        steps = service._extract_steps_from_history(history)

        self.assertEqual(len(steps), 2)
        self.assertTrue(all(step["target"] == "AI_AUTO" for step in steps))

    def test_extract_steps_from_history_uses_result_content_for_get_text(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(action=[FakeActionModel({"extract_content": {"index": 1}})]),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[SimpleNamespace(extracted_content="欢迎回来")],
                )
            ]
        )

        steps = service._extract_steps_from_history(history)

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["action"], "get_text")
        self.assertEqual(steps[0]["value"], "欢迎回来")

    def test_extract_steps_from_history_filters_empty_get_text(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(action=[FakeActionModel({"extract_content": {"index": 1}})]),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[SimpleNamespace(extracted_content="")],
                )
            ]
        )

        self.assertEqual(service._extract_steps_from_history(history), [])

    def test_extract_steps_from_history_returns_empty_without_history_attr(self):
        service = AgentService()
        self.assertEqual(service._extract_steps_from_history(SimpleNamespace()), [])

    def test_extract_steps_from_history_handles_none_history(self):
        service = AgentService()
        self.assertEqual(service._extract_steps_from_history(None), [])

    def test_extract_steps_from_history_handles_missing_model_output(self):
        service = AgentService()
        history = SimpleNamespace(history=[SimpleNamespace(model_output=None, state=None, result=[])])

        self.assertEqual(service._extract_steps_from_history(history), [])

    def test_extract_steps_from_history_handles_empty_action_list(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[SimpleNamespace(model_output=SimpleNamespace(action=[]), state=None, result=[])]
        )

        self.assertEqual(service._extract_steps_from_history(history), [])

    def test_build_step_identity_non_ai_auto_ignores_description(self):
        service = AgentService()
        first = {"action": "click", "target": "#submit", "value": "", "description": "a"}
        second = {"action": "click", "target": "#submit", "value": "", "description": "b"}

        self.assertEqual(service._build_step_identity(first), service._build_step_identity(second))

    def test_build_step_identity_ai_auto_uses_description_without_model(self):
        service = AgentService()
        first = {"action": "click", "target": "AI_AUTO", "value": "", "description": "a"}
        second = {"action": "click", "target": "AI_AUTO", "value": "", "description": "b"}

        self.assertNotEqual(service._build_step_identity(first), service._build_step_identity(second))

    def test_action_to_platform_step_marks_missing_interactive_target_as_ai_auto(self):
        service = AgentService()
        action_model = FakeActionModel({"click_element": {"index": 1}})

        step = service._action_to_platform_step(action_model)

        self.assertIsNotNone(step)
        self.assertEqual(step["target"], "AI_AUTO")
        self.assertEqual(step["action"], "click")

    def test_action_to_platform_step_keeps_fill_value_for_ai_auto(self):
        service = AgentService()
        action_model = FakeActionModel({"input_text": {"index": 3, "text": "admin"}})

        step = service._action_to_platform_step(action_model)

        self.assertIsNotNone(step)
        self.assertEqual(step["target"], "AI_AUTO")
        self.assertEqual(step["action"], "fill")
        self.assertEqual(step["value"], "admin")

    def test_extract_steps_from_history_retains_mixed_ai_auto_and_resolved_targets(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(
                        action=[
                            FakeActionModel({"click_element": {"index": 1}}),
                            FakeActionModel({"click_element": {"index": 7}}),
                        ]
                    ),
                    state=SimpleNamespace(
                        interacted_element=[FakeInteractedElement(7, "//button[@id='resolved']")]
                    ),
                    result=[],
                )
            ]
        )

        steps = service._extract_steps_from_history(history)

        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["target"], "AI_AUTO")
        self.assertEqual(steps[1]["target"], "//button[@id='resolved']")

    def test_extract_steps_from_history_handles_multiple_batches(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(action=[FakeActionModel({"click_element": {"index": 1}})]),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                ),
                SimpleNamespace(
                    model_output=SimpleNamespace(action=[FakeActionModel({"click_element": {"index": 2}})]),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                ),
            ]
        )

        steps = service._extract_steps_from_history(history)

        self.assertEqual(len(steps), 2)
        self.assertEqual([step["target"] for step in steps], ["AI_AUTO", "AI_AUTO"])

    def test_extract_steps_from_history_ignores_done_action(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(action=[FakeActionModel({"done": {"text": "完成"}})]),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                )
            ]
        )

        self.assertEqual(service._extract_steps_from_history(history), [])

    def test_build_step_identity_uses_action_payload_for_same_description(self):
        service = AgentService()
        first_action = FakeActionModel({"click_element": {"index": 1}})
        second_action = FakeActionModel({"click_element": {"index": 2}})
        step = {
            "action": "click",
            "target": "AI_AUTO",
            "value": "",
            "description": "点击登录按钮",
        }

        self.assertNotEqual(
            service._build_step_identity(step, first_action),
            service._build_step_identity(step, second_action),
        )

    def test_extract_steps_from_history_keeps_same_action_different_values(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(
                        action=[
                            FakeActionModel({"input_text": {"index": 1, "text": "admin"}}),
                            FakeActionModel({"input_text": {"index": 1, "text": "123456"}}),
                        ]
                    ),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                )
            ]
        )

        steps = service._extract_steps_from_history(history)

        self.assertEqual(len(steps), 2)
        self.assertEqual([step["value"] for step in steps], ["admin", "123456"])

    def test_extract_steps_from_history_keeps_same_ai_auto_description_different_payloads(self):
        service = AgentService()
        history = SimpleNamespace(
            history=[
                SimpleNamespace(
                    model_output=SimpleNamespace(
                        action=[
                            FakeActionModel({"click_element": {"index": 11}}),
                            FakeActionModel({"click_element": {"index": 12}}),
                        ]
                    ),
                    state=SimpleNamespace(interacted_element=[]),
                    result=[],
                )
            ]
        )

        steps = service._extract_steps_from_history(history)

        self.assertEqual(len(steps), 2)
        self.assertEqual([step["description"] for step in steps], [
            "点击元素: AI_AUTO",
            "点击元素: AI_AUTO",
        ])

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
