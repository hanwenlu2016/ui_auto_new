"""
应用配置模块

本模块使用 Pydantic Settings 管理应用的所有配置项：
- 数据库连接配置 (PostgreSQL)
- Redis 缓存配置
- Celery 任务队列配置
- JWT 安全配置
- 浏览器自动化配置

配置优先级：环境变量 > .env 文件 > 默认值
"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    应用配置类
    
    所有配置项都可以通过环境变量覆盖，环境变量名与属性名相同。
    例如：export DATABASE_URL="postgresql://..."
    """
    PROJECT_NAME: str = "UI Automation Platform"
    
    # 数据库配置
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "123456"
    POSTGRES_DB: str = "ui_auto_db"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: Optional[str] = None

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery 配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # 安全配置
    SECRET_KEY: str = "YOUR_SECRET_KEY_HERE_PLEASE_CHANGE_IT"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 浏览器配置
    BROWSER_HEADLESS: bool = True  # True=无头模式, False=有头模式
    BROWSER_TYPE: str = "chromium"  # chromium, firefox, webkit

    def __init__(self, **kwargs):
        """
        初始化配置，自动构建数据库连接字符串
        """
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        """Pydantic 配置"""
        case_sensitive = True

# 全局配置实例
settings = Settings()
