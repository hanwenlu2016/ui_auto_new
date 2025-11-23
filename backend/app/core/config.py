from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "UI Automation Platform"
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "123456"
    POSTGRES_DB: str = "ui_auto_db"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "YOUR_SECRET_KEY_HERE_PLEASE_CHANGE_IT"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Browser Configuration
    BROWSER_HEADLESS: bool = True  # True=无头模式, False=有头模式
    BROWSER_TYPE: str = "chromium"  # chromium, firefox, webkit

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        case_sensitive = True

settings = Settings()
