from typing import Optional
from pydantic import BaseModel
from datetime import datetime

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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    creator_id: Optional[int] = None
    updater_id: Optional[int] = None
    creator_name: Optional[str] = None
    updater_name: Optional[str] = None
    
    class Config:
        from_attributes = True
