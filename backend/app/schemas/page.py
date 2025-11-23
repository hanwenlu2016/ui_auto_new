from typing import Optional
from pydantic import BaseModel

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
    
    class Config:
        from_attributes = True
