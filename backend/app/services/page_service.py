from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.page import Page
from app.schemas.page import PageCreate, PageUpdate
from app.services.base import CRUDBase

class PageService(CRUDBase[Page, PageCreate, PageUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(Page)

    async def get_by_module(self, db: AsyncSession, module_id: int) -> List[Page]:
        query = select(self.model).where(self.model.module_id == module_id)
        result = await db.execute(query)
        return result.scalars().all()
