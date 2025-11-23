from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class TestReportBase(BaseModel):
    test_case_id: Optional[int] = None
    test_suite_id: Optional[int] = None
    executor_id: Optional[int] = None
    report_path: str
    status: str
    browser_type: str = "chromium"
    headless: bool = True
    error_message: Optional[str] = None

class TestReportCreate(TestReportBase):
    pass

class TestReportUpdate(BaseModel):
    status: Optional[str] = None
    error_message: Optional[str] = None

class TestReport(TestReportBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TestReportWithDetails(TestReport):
    """Report with test case name and executor name"""
    test_case_name: Optional[str] = None
    executor_name: Optional[str] = None
    report_url: Optional[str] = None
