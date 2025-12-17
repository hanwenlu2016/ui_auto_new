from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class PageBase(BaseModel):
    name: str
    description: Optional[str] = None

class PageCreate(PageBase):
    module_id: int

class PageUpdate(PageBase):
    pass

class Page(PageBase):
    id: int
    module_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    creator_id: Optional[int] = None
    updater_id: Optional[int] = None
    creator_name: Optional[str] = None
    updater_name: Optional[str] = None
    
    class Config:
        from_attributes = True
