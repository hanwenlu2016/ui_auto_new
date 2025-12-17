from app.services.base import CRUDBase
from app.models.module import Module
from app.schemas.module import ModuleCreate, ModuleUpdate
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, aliased
from datetime import datetime
from app.models.user import User

class ModuleService(CRUDBase[Module, ModuleCreate, ModuleUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: ModuleCreate, creator_id: int = None, updater_id: int = None) -> Module:
        # Check if module with same name exists in the project
        result = await db.execute(
            select(Module)
            .where(Module.project_id == obj_in.project_id)
            .where(Module.name == obj_in.name)
        )
        if result.scalars().first():
            raise ValueError(f"Module with name '{obj_in.name}' already exists in this project")
        
        # Add creator/updater info to obj_in if not present in schema but needed for DB
        obj_in_data = obj_in.model_dump()
        if creator_id:
            obj_in_data["creator_id"] = creator_id
        if updater_id:
            obj_in_data["updater_id"] = updater_id
            
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_multi(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100, 
        filters: dict = None,
        name: str = None,
        created_after: datetime = None,
        created_before: datetime = None,
        creator: str = None,
        updater: str = None
    ) -> list[Module]:
        query = select(self.model).options(
            selectinload(Module.creator),
            selectinload(Module.updater)
        )
        if filters:
            for attr, value in filters.items():
                if hasattr(self.model, attr) and value is not None:
                    query = query.where(getattr(self.model, attr) == value)
        
        if name:
            query = query.where(Module.name.ilike(f"%{name}%"))
            
        if created_after:
            query = query.where(Module.created_at >= created_after)
            
        if created_before:
            query = query.where(Module.created_at <= created_before)
            
        if creator:
            Creator = aliased(User)
            query = query.join(Module.creator.of_type(Creator)).where(
                or_(Creator.full_name.ilike(f"%{creator}%"), Creator.email.ilike(f"%{creator}%"))
            )
            
        if updater:
            Updater = aliased(User)
            query = query.join(Module.updater.of_type(Updater)).where(
                or_(Updater.full_name.ilike(f"%{updater}%"), Updater.email.ilike(f"%{updater}%"))
            )
        
        result = await db.execute(query.offset(skip).limit(limit))
        modules = result.scalars().all()
        
        # Populate creator_name and updater_name for Pydantic schema
        for module in modules:
            if module.creator:
                module.creator_name = module.creator.full_name or module.creator.email
            if module.updater:
                module.updater_name = module.updater.full_name or module.updater.email
                
        return modules

module_service = ModuleService(Module)
