from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_url: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
