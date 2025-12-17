from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("modules.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updater_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    project = relationship("Project", back_populates="modules")
    parent = relationship("Module", remote_side=[id], backref="children")
    pages = relationship("Page", back_populates="module", cascade="all, delete-orphan")
    test_cases = relationship("TestCase", back_populates="module", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[creator_id])
    updater = relationship("User", foreign_keys=[updater_id])
