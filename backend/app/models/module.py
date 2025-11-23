from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("modules.id"), nullable=True)
    
    project = relationship("Project", back_populates="modules")
    parent = relationship("Module", remote_side=[id], backref="children")
    pages = relationship("Page", back_populates="module", cascade="all, delete-orphan")
    test_cases = relationship("TestCase", back_populates="module", cascade="all, delete-orphan")
