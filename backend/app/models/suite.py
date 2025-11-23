from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.associations import test_suite_cases

class TestSuite(Base):
    __tablename__ = "test_suites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    project = relationship("Project", back_populates="test_suites")
    test_cases = relationship("TestCase", secondary=test_suite_cases, back_populates="test_suites")
