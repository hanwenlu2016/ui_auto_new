from typing import Optional
from pydantic import BaseModel

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

    class Config:
        from_attributes = True
