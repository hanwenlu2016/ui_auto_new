from typing import Optional
from pydantic import BaseModel

class ModuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None

class ModuleCreate(ModuleBase):
    project_id: int

class ModuleUpdate(ModuleBase):
    pass

class Module(ModuleBase):
    id: int
    project_id: int
    
    class Config:
        from_attributes = True
