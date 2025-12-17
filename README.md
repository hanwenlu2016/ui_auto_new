# Intelligent UI Automation Platform

A modern, enterprise-grade UI automation testing platform built with Python (FastAPI) and Vue 3. It utilizes Playwright for robust browser automation and integrates AI capabilities for simplified test creation.

## ✨ Key Features

### 🚀 Core Automation
-   **Page Object Model (POM)**: Structured management of Pages and UI Elements to ensure test maintainability.
-   **Multi-Browser Support**: Seamless execution on Chromium, Firefox, and WebKit (via Playwright).
-   **Distributed Execution**: Asynchronous test execution using Celery and Redis.

### 🎥 Smart Recording
-   **Interactive Recording**: Built-in browser recorder that captures user actions and converts them into test steps.
-   **Project Context**: Automatically detects the active project and configures the recording environment (Base URL).
-   **Smart Element Detection**: Captures robust selectors and allows for immediate replay.

### 🤖 AI-Assisted Generation
-   **Natural Language to Test**: Describe your test case in plain English (e.g., *"Open Google and search for Python"*), and the embedded AI engine generates the executable steps automatically.
-   **Heuristic Parsing**: Intelligent parsing of actions like `goto`, `click`, `fill`, and `wait`.

### 📊 Reporting & Analytics
-   **Allure Integration**: Generates detailed, interactive test reports with screenshots and logs.
-   **Data Isolation**: Ensures every test run has clean, isolated results, avoiding historical data contamination.

## 🛠 Technology Stack

### Backend
-   **Framework**: FastAPI (Python 3.12+)
-   **Database**: PostgreSQL / SQLite (with SQLAlchemy Async)
-   **Task Queue**: Celery + Redis
-   **Automation**: Playwright
-   **Testing**: Pytest

### Frontend
-   **Framework**: Vue 3 + TypeScript
-   **Build Tool**: Vite
-   **UI Library**: Naive UI
-   **State Management**: Pinia (implied)

## ⚡️ Quick Start

### Prerequisites
-   Python 3.12+
-   Node.js 18+
-   Redis (for Task Queue)

### Backend Setup
1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Install dependencies (using `uv` or `pip`):
    ```bash
    uv sync  # or pip install -r requirements.txt
    ```
3.  Start the API Server:
    ```bash
    uv run uvicorn app.main:app --reload
    ```
4.  Start the Celery Worker (for executing tests):
    ```bash
    celery -A app.core.celery_app worker --loglevel=info
    ```

### Frontend Setup
1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the development server:
    ```bash
    npm run dev
    ```

## 📝 Usage Guide

1.  **Create a Project**: Go to **Projects** and define a new web project with a Base URL.
2.  **Record a Case**:
    -   Go to **Recording**.
    -   Select your project and click **Start Recording**.
    -   Interact with the browser.
    -   Click **Stop** and **Save Case**.
3.  **AI Generation**:
    -   Go to **Test Cases** -> **Create Case**.
    -   Click **✨ AI Generate**.
    -   Type your command (e.g., "Open http://localhost:5173 and click Login").
    -   Click **Generate** to create steps.
4.  **Run & Report**:
    -   Click **Run** on any test case or suite.
    -   View the results in the **Reports** section.
