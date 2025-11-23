from app.services.base import CRUDBase
from app.models.module import Module
from app.schemas.module import ModuleCreate, ModuleUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class ModuleService(CRUDBase[Module, ModuleCreate, ModuleUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: ModuleCreate) -> Module:
        # Check if module with same name exists in the project
        result = await db.execute(
            select(Module)
            .where(Module.project_id == obj_in.project_id)
            .where(Module.name == obj_in.name)
        )
        if result.scalars().first():
            raise ValueError(f"Module with name '{obj_in.name}' already exists in this project")
        return await super().create(db, obj_in=obj_in)

module_service = ModuleService(Module)
