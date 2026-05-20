# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend
```bash
# Start dev server (from backend/)
uv run uvicorn app.main:app --reload

# Install deps
uv sync

# Run Celery worker (for async test execution)
celery -A app.core.celery_app worker --loglevel=info

# Alembic migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Frontend
```bash
# Start dev server (from frontend/)
npm run dev

# Install deps
npm install

# Build
npm run build

# Preview production build
npm run preview
```

## Project Architecture

A UI automation testing platform with Playwright browser automation, AI-powered test generation, and self-healing capabilities.

### Backend Structure (`backend/app/`)

**API Layer** (`api/v1/endpoints/`): Thin route handlers that validate input (Pydantic), delegate to services, and return responses. All endpoints require auth via `deps.get_current_user`. Key endpoints:

| Endpoint | Prefix | Purpose |
|---|---|---|
| `login.py` | `/login` | JWT auth |
| `projects.py` | `/projects` | CRUD projects (each has base_url) |
| `modules.py` | `/modules` | CRUD modules (belong to a project) |
| `pages.py` | `/pages` | CRUD pages (belong to a module) |
| `elements.py` | `/elements` | CRUD page elements (belong to a page) |
| `cases.py` | `/cases` | CRUD test cases (belong to a module, have steps) |
| `suites.py` | `/suites` | CRUD test suites (aggregate test cases) |
| `execution.py` | `/execution` | Trigger async test run via Celery |
| `recording.py` | `/recording` | Browser recording sessions |
| `reports.py` | `/reports` | Test reports (Allure) |
| `ai.py` | `/ai` | AI generate/discover/heal/feedback |
| `ai_models.py` | `/ai-models` | CRUD AI model configs |
| `agent.py` | `/agent` | AI Agent execution endpoints (browser-use) |
| `dashboard.py` | `/dashboard` | Stats and metrics |

**Service Layer** (`services/`): Business logic. All services inherit from `CRUDBase` (in `base.py`) providing `get/get_multi/create/update/remove`. Key services:
- `ai_service.py` — 4 AI modules: generate steps, discover page elements, heal selectors, RLHF feedback. Provider-agnostic (OpenAI-compatible), model config stored in `ai_models` DB table. Caches `AsyncOpenAI` clients per model ID, invalidates on config change.
- `runner.py` — `TestRunner` executes test cases via Playwright. Handles selector resolution (Page Object → multi-strategy locator chain → raw target → semantic healing → visual matching), Allure result generation, and heal log recording.
- `recorder.py` — Browser recording session management.

**Models** (`models/`): SQLAlchemy models. Entity hierarchy: Project → Module → Page → PageElement. TestCase has JSON `steps` field. HealLog records selector failures and repairs. StepFeedback stores RLHF data.

**Schema** (`schemas/`): Pydantic models for request/response validation. Matches models 1:1.

**Core** (`core/`):
- `config.py` — `Settings` via pydantic-settings, env/configurable (DB, Redis, JWT, browser)
- `celery_app.py` — Celery instance
- `security.py` — JWT token create/verify
- `logger.py` — Logging setup

**Worker** (`worker.py`): Celery task definitions. `run_test_case_task` and `run_test_suite_task` — each creates an isolated DB session, invokes `TestRunner`, generates Allure report, cleans up temp dirs.

### Frontend Structure (`frontend/src/`)

**Views** (`views/`): One per route — `Login.vue`, `Dashboard.vue`, `Projects.vue`, `Modules.vue`, `Pages.vue`, `PageElements.vue`, `TestCases.vue`, `TestSuites.vue`, `Recording.vue`, `Reports.vue`, `AIModels.vue`.

**Components** (`components/`): `AIChatConsole.vue` — reusable AI chat dialog for generating test steps.

**Stores** (`stores/`): Pinia stores — `user.ts` (auth token, user info), `app.ts`, `recording.ts` (pending steps buffer), `tab.ts`.

**Utils** (`utils/`): `aiCaseFlow.ts` — step normalization functions shared between AI generation and manual editing. `aiContext.ts` — DOM extraction for AI context.

**API** (`api/`): Axios client with JWT Bearer token interceptor and 401 redirect.

**Router** (`router/`): Vue Router with auth guard. Main layout wraps all authenticated routes.

### Key Data Flows

1. **AI Test Generation**: User prompt → `POST /api/v1/ai/generate` → `AIService.generate_steps_from_text()` (LLM call) → optional `bind_steps_to_library()` (matches generated steps to existing Page Elements) → returned as processable step objects.

2. **Test Execution**: `POST /execution/cases/{id}/run` → Celery task → `TestRunner.run_test_case()` → Playwright executes steps (resolving selectors via Page Object library → multi-strategy locator chain → raw target → semantic healing → visual matching) → Allure results generated → report stored.

3. **Self-Healing**: Step fails → `_try_selectors()` tries all selector candidates → if all fail and action is interactive → Tier 1 semantic healing (`_find_semantic_selector()`) → Tier 2 visual matching (`_visual_match()`) → `_write_heal_log()` records the healing.

4. **AI Model Config**: `ai_models` DB table stores api_key/base_url/model_identifier. `AIService._get_client_from_db()` fetches by ID or default, caches AsyncOpenAI clients, invalidates on config fingerprint change.

### Important Patterns

- **Multi-Strategy Locator Chain**: Each element stores 5 independent selector strategies (`strategy_role`, `strategy_attr`, `strategy_text`, `strategy_label`, `strategy_xpath`) plus backward-compatible `primary/fallback_1/fallback_2/fallback_3`. Each strategy uses a different mechanism (role, attribute, text, label, XPath) so they fail independently rather than cascading.
- **RLHF**: User feedback (thumbs up/down, corrections) stored as `StepFeedback`, injected into future AI prompts as project memory.
- **CRUD pattern**: Create a new service = extend `CRUDBase[Model, CreateSchema, UpdateSchema]`, then mount in endpoints. See any existing service file for the pattern.
