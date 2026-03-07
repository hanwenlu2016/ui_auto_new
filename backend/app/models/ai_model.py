from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class AIModel(Base):
    """
    AI 模型配置持久化模型
    存储各厂商的模型名称、地址、API Key 等动态配置
    """
    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)     # 友好显示名称 (例: "DeepSeek 官方")
    base_url = Column(String, nullable=False)            # API 基础地址
    api_key = Column(String, nullable=False)             # API 密钥
    model_identifier = Column(String, nullable=False)    # 模型标识符 (例: "deepseek-chat")
    is_default = Column(Boolean, default=False)          # 是否为系统默认模型
    is_active = Column(Boolean, default=True)            # 是否启用
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
