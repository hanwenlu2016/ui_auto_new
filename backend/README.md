# UI Automation Backend

基于 FastAPI 的高性能测试引擎。

## 💡 核心模块
- **AI Service**: 集成 MiniMax 大模型，支持 Super-Prompt 多模态解析与多场景生成。
- **Core Engine**: 基于 Playwright 的分布式执行引擎，支持选择器自愈逻辑。
- **Task Queue**: Celery + Redis 异步处理百万级测试用例下发。
- **RLHF Layer**: 记录用户对 AI 步骤的反馈，用于持续微调提示词策略。
