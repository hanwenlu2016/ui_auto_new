from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    
    module = relationship("Module", back_populates="pages")
    page_elements = relationship("PageElement", back_populates="page", cascade="all, delete-orphan")
