from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
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
    
    page = relationship("Page", back_populates="page_elements")
