from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class PageElementBase(BaseModel):
    name: str
    description: Optional[str] = None
    locator_type: str
    locator_value: str

class PageElementCreate(PageElementBase):
    page_id: int

class PageElementUpdate(PageElementBase):
    pass

class PageElement(PageElementBase):
    id: int
    page_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    creator_id: Optional[int] = None
    updater_id: Optional[int] = None
    creator_name: Optional[str] = None
    updater_name: Optional[str] = None

    class Config:
        from_attributes = True
