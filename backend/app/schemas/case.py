from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime

class TestStep(BaseModel):
    action: str  # click, fill, goto, etc.
    element_id: Optional[int] = None
    target: Optional[str] = None
    selector: Optional[str] = None
    value: Optional[str] = None
    wait_ms: Optional[int] = None
    locator_chain: Optional[Dict[str, Any]] = None
    variable_name: Optional[str] = None
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
    updater_id: Optional[int] = None
    creator_name: Optional[str] = None
    updater_name: Optional[str] = None

    class Config:
        from_attributes = True
