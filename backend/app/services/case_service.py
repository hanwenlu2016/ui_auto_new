from app.services.base import CRUDBase
from app.models.case import TestCase
from app.models.module import Module
from app.schemas.case import TestCaseCreate, TestCaseUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

class CaseService(CRUDBase[TestCase, TestCaseCreate, TestCaseUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: TestCaseCreate, **kwargs) -> TestCase:
        # If name already exists in the module, auto-append a numeric suffix
        base_name = obj_in.name
        candidate = base_name
        counter = 2
        while True:
            result = await db.execute(
                select(TestCase)
                .where(TestCase.module_id == obj_in.module_id)
                .where(TestCase.name == candidate)
            )
            if not result.scalars().first():
                break
            candidate = f"{base_name} ({counter})"
            counter += 1

        # Use a mutable copy with the resolved unique name
        obj_data = obj_in.model_dump()
        obj_data["name"] = candidate
        db_obj = TestCase(**obj_data, **kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

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

    async def remove(self, db: AsyncSession, *, id: int) -> TestCase:
        from app.models.heal_log import HealLog
        from app.models.report import TestReport
        from sqlalchemy import delete
        
        result = await db.execute(select(self.model).where(self.model.id == id))
        obj = result.scalars().first()
        if obj:
            # Delete dependent records first to prevent foreign key constraint violations
            await db.execute(delete(HealLog).where(HealLog.case_id == id))
            await db.execute(delete(TestReport).where(TestReport.test_case_id == id))
            
            await db.delete(obj)
            await db.commit()
        return obj

case_service = CaseService(TestCase)
