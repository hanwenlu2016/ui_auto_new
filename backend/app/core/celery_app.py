"""
Celery 应用实例模块

本模块创建和配置 Celery 应用实例，用于异步任务队列管理。

配置项：
- broker: Redis 消息代理
- result_backend: Redis 结果存储后端
"""
from celery import Celery
from app.core.config import settings

# 创建 Celery 应用实例
celery_app = Celery("worker", broker=settings.CELERY_BROKER_URL)

# 配置结果后端
celery_app.conf.update(
    result_backend=settings.CELERY_RESULT_BACKEND,
)
