from app.services.base import CRUDBase
from app.models.element import PageElement
from app.schemas.element import PageElementCreate, PageElementUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List

class ElementService(CRUDBase[PageElement, PageElementCreate, PageElementUpdate]):
    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, filters: dict = None
    ) -> List[PageElement]:
        query = select(self.model).options(
            selectinload(PageElement.creator),
            selectinload(PageElement.updater)
        )
        if filters:
            for attr, value in filters.items():
                if hasattr(self.model, attr) and value is not None:
                    query = query.where(getattr(self.model, attr) == value)
        
        result = await db.execute(query.offset(skip).limit(limit))
        elements = result.scalars().all()
        
        for element in elements:
            if element.creator:
                element.creator_name = element.creator.full_name or element.creator.email
            if element.updater:
                element.updater_name = element.updater.full_name or element.updater.email
                
        return elements

element_service = ElementService(PageElement)
