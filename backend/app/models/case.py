from sqlalchemy import Column, Integer, String, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.associations import test_suite_cases

class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    priority = Column(String, default="P1")
    status = Column(String, default="draft")  # draft, active, deprecated
    steps = Column(JSON, default=list)  # List of steps with action, element_id, value, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    creator_id = Column(Integer, ForeignKey("users.id"))

    module = relationship("Module", back_populates="test_cases")
    creator = relationship("User")
    test_suites = relationship("TestSuite", secondary=test_suite_cases, back_populates="test_cases")
