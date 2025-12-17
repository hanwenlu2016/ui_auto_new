from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.page import Page
from app.schemas.page import PageCreate, PageUpdate
from app.services.base import CRUDBase

class PageService(CRUDBase[Page, PageCreate, PageUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(Page)

    async def get_by_module(self, db: AsyncSession, module_id: int) -> List[Page]:
        query = select(self.model).options(
            selectinload(Page.creator),
            selectinload(Page.updater)
        ).where(self.model.module_id == module_id)
        result = await db.execute(query)
        pages = result.scalars().all()
        
        for page in pages:
            if page.creator:
                page.creator_name = page.creator.full_name or page.creator.email
            if page.updater:
                page.updater_name = page.updater.full_name or page.updater.email
                
        return pages

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, filters: dict = None
    ) -> List[Page]:
        query = select(self.model).options(
            selectinload(Page.creator),
            selectinload(Page.updater)
        )
        if filters:
            for attr, value in filters.items():
                if hasattr(self.model, attr) and value is not None:
                    query = query.where(getattr(self.model, attr) == value)
        
        result = await db.execute(query.offset(skip).limit(limit))
        pages = result.scalars().all()
        
        for page in pages:
            if page.creator:
                page.creator_name = page.creator.full_name or page.creator.email
            if page.updater:
                page.updater_name = page.updater.full_name or page.updater.email
                
        return pages
