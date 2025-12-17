from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class PageElement(Base):
    __tablename__ = "page_elements"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=True) # Deprecated, kept for migration safety if needed, or just remove. Let's remove it to enforce new schema.
    # Actually, let's just replace it.
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    locator_type = Column(String, nullable=False)  # xpath, css, id, name, etc.
    locator_value = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updater_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    page = relationship("Page", back_populates="page_elements")
    creator = relationship("User", foreign_keys=[creator_id])
    updater = relationship("User", foreign_keys=[updater_id])
