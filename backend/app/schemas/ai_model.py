from typing import Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime

# Shared properties
class AIModelBase(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_identifier: Optional[str] = None
    is_default: Optional[bool] = False
    is_active: Optional[bool] = True

# Properties to receive on model creation
class AIModelCreate(AIModelBase):
    name: str
    base_url: str
    api_key: str
    model_identifier: str

# Properties to receive on model update
class AIModelUpdate(AIModelBase):
    pass

# Properties to return to client
class AIModel(AIModelBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
