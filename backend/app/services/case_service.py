from app.services.base import CRUDBase
from app.models.case import TestCase
from app.models.module import Module
from app.schemas.case import TestCaseCreate, TestCaseUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

class CaseService(CRUDBase[TestCase, TestCaseCreate, TestCaseUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: TestCaseCreate, **kwargs) -> TestCase:
        # Check if case with same name exists in the module
        result = await db.execute(
            select(TestCase)
            .where(TestCase.module_id == obj_in.module_id)
            .where(TestCase.name == obj_in.name)
        )
        if result.scalars().first():
            raise ValueError(f"Test case with name '{obj_in.name}' already exists in this module")
        return await super().create(db, obj_in=obj_in, **kwargs)

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, filters: dict = None
    ) -> list[TestCase]:
        query = select(self.model)
        if filters:
            if "project_id" in filters:
                project_id = filters.pop("project_id")
                query = query.join(Module).where(Module.project_id == project_id)
            
            for attr, value in filters.items():
                if hasattr(self.model, attr) and value is not None:
                    query = query.where(getattr(self.model, attr) == value)
        
        # Add eager loading for creator and updater
        query = query.options(
            selectinload(TestCase.creator),
            selectinload(TestCase.updater)
        )
        
        result = await db.execute(query.offset(skip).limit(limit))
        cases = result.scalars().all()
        
        for case in cases:
            if case.creator:
                case.creator_name = case.creator.full_name or case.creator.email
            if case.updater:
                case.updater_name = case.updater.full_name or case.updater.email
                
        return cases

case_service = CaseService(TestCase)
