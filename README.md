# 智能 UI 自动化测试平台 (Intelligent UI Automation Platform)

基于 Python (FastAPI) 和 Vue 3 构建的现代化、企业级 UI 自动化测试平台。它利用 Playwright 实现强大的浏览器自动化，并集成了 AI 能力以简化测试用例的创建。

## 🏗 架构设计图

```mermaid
graph TD
    Client[用户浏览器 (Frontend)] -->|HTTP/REST| API[后端 API (FastAPI)]
    
    subgraph "后端服务 (Backend)"
        API -->|CRUD| DB[(数据库 PostgreSQL/SQLite)]
        API -->|解析指令| AI[AI 服务 (Heuristic/LLM)]
        API -->|分发任务| Redis[(Redis 消息队列)]
    end
    
    subgraph "执行引擎 (Worker)"
        Worker[Celery Worker] -->|消费任务| Redis
        Worker -->|控制| PW[Playwright 浏览器]
        PW -->|自动化操作| Target[目标网站]
        Worker -->|生成| Report[Allure 报告]
        Report -->|存储| Disk[文件系统]
    end
    
    Client -->|查看| Report
```

## ✨ 核心功能

### 🚀 核心自动化能力
-   **Page Object Model (POM)**: 结构化管理页面和 UI 元素，确保测试的可维护性。
-   **多浏览器支持**: 无缝支持 Chromium, Firefox, 和 WebKit (通过 Playwright)。
-   **分布式执行**: 使用 Celery 和 Redis 实现异步测试执行。

### 🎥 智能录制
-   **交互式录制**: 内置浏览器录制器，可捕获用户操作并将其转换为测试步骤。
-   **项目上下文感知**: 自动检测当前项目并配置录制环境（如 Base URL）。
-   **智能元素检测**: 捕获健壮的选择器 (Selector) 并支持立即回放验证。

### 🤖 AI 辅助生成 (✨ 新功能)
-   **自然语言转测试**: 用自然语言描述测试用例（例如："打开百度并搜索 Python"），内置 AI 引擎会自动生成可执行的步骤。
-   **启发式解析**: 智能解析 `goto` (跳转), `click` (点击), `fill` (输入), 和 `wait` (等待) 等动作。

### 📊 报告与分析
-   **Allure 集成**: 生成包含截图和日志的详细交互式测试报告。
-   **数据隔离**: 确保每次测试运行都有干净、隔离的结果，避免历史数据污染。

## 🛠 技术栈

### 后端 (Backend)
-   **框架**: FastAPI (Python 3.12+)
-   **数据库**: PostgreSQL / SQLite (使用 SQLAlchemy Async)
-   **任务队列**: Celery + Redis
-   **自动化引擎**: Playwright
-   **测试框架**: Pytest

### 前端 (Frontend)
-   **框架**: Vue 3 + TypeScript
-   **构建工具**: Vite
-   **UI 组件库**: Naive UI
-   **状态管理**: Pinia

## ⚡️ 快速开始

### 前置要求
-   Python 3.12+
-   Node.js 18+
-   Redis (用于任务队列)

### 后端设置
1.  进入后端目录:
    ```bash
    cd backend
    ```
2.  安装依赖 (使用 `uv` 或 `pip`):
    ```bash
    uv sync  # 或者 pip install -r requirements.txt
    ```
3.  启动 API 服务:
    ```bash
    uv run uvicorn app.main:app --reload
    ```
4.  启动 Celery Worker (用于执行测试):
    ```bash
    celery -A app.core.celery_app worker --loglevel=info
    ```

### 前端设置
1.  进入前端目录:
    ```bash
    cd frontend
    ```
2.  安装依赖:
    ```bash
    npm install
    ```
3.  启动开发服务器:
    ```bash
    npm run dev
    ```

## 📝 使用指南

1.  **创建项目**: 进入 **项目管理 (Projects)**，定义一个新的 Web 项目并设置 Base URL。
2.  **录制用例**:
    -   进入 **录制 (Recording)** 页面。
    -   选择你的项目并点击 **开始录制**。
    -   在浏览器中进行操作。
    -   点击 **停止** 并 **保存用例**。
3.  **AI 生成**:
    -   进入 **测试用例 (Test Cases)** -> **创建用例**。
    -   点击 **✨ AI 生成** 按钮。
    -   输入指令 (例如: "Open http://localhost:5173 and click Login")。
    -   点击 **生成**，系统将自动填充步骤。
4.  **运行与报告**:
    -   在测试用例或套件上点击 **运行**。
    -   在 **测试报告 (Reports)** 页面查看详细的 Allure 结果。
