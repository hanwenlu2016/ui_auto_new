from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime

class TestStep(BaseModel):
    action: str  # click, fill, goto, etc.
    element_id: Optional[int] = None
    value: Optional[str] = None
    description: Optional[str] = None

class TestCaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    priority: Optional[str] = "P1"
    status: Optional[str] = "draft"
    steps: List[Dict[str, Any]] = []

class TestCaseCreate(TestCaseBase):
    module_id: int

class TestCaseUpdate(TestCaseBase):
    pass

class TestCase(TestCaseBase):
    id: int
    module_id: int
    creator_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
