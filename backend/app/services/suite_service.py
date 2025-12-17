from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.base import CRUDBase
from app.models.suite import TestSuite
from app.models.case import TestCase
from app.schemas.suite import TestSuiteCreate, TestSuiteUpdate

class SuiteService(CRUDBase[TestSuite, TestSuiteCreate, TestSuiteUpdate]):
    async def get(self, db: AsyncSession, id: Any) -> Optional[TestSuite]:
        from sqlalchemy.orm import selectinload
        stmt = select(TestSuite).options(selectinload(TestSuite.test_cases)).where(TestSuite.id == id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, filters: dict = None
    ) -> List[TestSuite]:
        from sqlalchemy.orm import selectinload
        stmt = select(TestSuite).options(
            selectinload(TestSuite.test_cases),
            selectinload(TestSuite.creator),
            selectinload(TestSuite.updater)
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(TestSuite, key):
                    stmt = stmt.where(getattr(TestSuite, key) == value)
                    
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        suites = result.scalars().all()
        
        for suite in suites:
            if suite.creator:
                suite.creator_name = suite.creator.full_name or suite.creator.email
            if suite.updater:
                suite.updater_name = suite.updater.full_name or suite.updater.email
                
        return suites

    async def create(self, db: AsyncSession, *, obj_in: TestSuiteCreate, **kwargs) -> TestSuite:
        db_obj = TestSuite(
            name=obj_in.name,
            description=obj_in.description,
            project_id=obj_in.project_id
        )
        
        if obj_in.test_case_ids:
            result = await db.execute(select(TestCase).where(TestCase.id.in_(obj_in.test_case_ids)))
            test_cases = result.scalars().all()
            db_obj.test_cases = list(test_cases)
            
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        # Re-fetch with eager loading to ensure relationship is available for Pydantic
        return await self.get(db, db_obj.id)

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: TestSuite,
        obj_in: TestSuiteUpdate
    ) -> TestSuite:
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"test_case_ids"})
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        if obj_in.test_case_ids is not None:
            result = await db.execute(select(TestCase).where(TestCase.id.in_(obj_in.test_case_ids)))
            test_cases = result.scalars().all()
            db_obj.test_cases = list(test_cases)
            
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        # Re-fetch with eager loading
        return await self.get(db, db_obj.id)

suite_service = SuiteService(TestSuite)
