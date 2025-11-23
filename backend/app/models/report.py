from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class TestReport(Base):
    __tablename__ = "test_reports"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=True)
    test_suite_id = Column(Integer, ForeignKey("test_suites.id"), nullable=True)
    executor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    report_path = Column(String, nullable=False)
    status = Column(String, nullable=False)  # success, failure
    browser_type = Column(String, default="chromium")
    headless = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    test_case = relationship("TestCase", backref="reports")
    test_suite = relationship("TestSuite", backref="reports")
    executor = relationship("User", backref="executed_reports")
