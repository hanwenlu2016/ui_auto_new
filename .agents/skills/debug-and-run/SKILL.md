---
name: debug-and-run
description: 本地启动、调试和排查本项目问题。包括启动后端、前端、Celery Worker，以及常见错误的排查方法。
---

# 项目启动与调试指南

## 服务架构

本项目包含 4 个需要同时运行的服务：

| 服务 | 技术 | 端口 | 命令 |
|------|------|------|------|
| 后端 API | FastAPI | 8000 | `uv run uvicorn app.main:app --reload` |
| 前端 | Vite/Vue3 | 5173 | `npm run dev` |
| 任务队列 | Celery | - | `celery -A app.core.celery_app worker` |

## 快速启动


### 1. 启动后端

```bash
cd backend
ource .venv/bin/activate
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 启动 Celery Worker

```bash
cd backend
ource .venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
# 调试模式 (单进程，方便查看日志):
celery -A app.core.celery_app worker --loglevel=debug --concurrency=1 --pool=solo
```

### 3 启动前端

```bash
cd frontend
npm run dev
```

## 日志文件位置

```
backend/backend_proper.log    # 后端 API 运行日志
backend/celery_proper.log     # Celery 任务执行日志
frontend/frontend_proper.log  # 前端构建日志
backend/allure-results/       # 测试结果（含截图）
```

## API 文档

后端启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json






