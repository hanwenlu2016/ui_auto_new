from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.schemas.case import TestCase

class TestSuiteBase(BaseModel):
    name: str
    description: Optional[str] = None

class TestSuiteCreate(TestSuiteBase):
    project_id: int
    test_case_ids: List[int] = []

class TestSuiteUpdate(TestSuiteBase):
    test_case_ids: Optional[List[int]] = None

class TestSuite(TestSuiteBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    creator_id: Optional[int] = None
    updater_id: Optional[int] = None
    creator_name: Optional[str] = None
    updater_name: Optional[str] = None
    test_cases: List[TestCase] = []

    class Config:
        from_attributes = True
