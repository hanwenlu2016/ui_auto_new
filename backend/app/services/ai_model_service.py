from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.ai_model import AIModel
from app.schemas.ai_model import AIModelCreate, AIModelUpdate

class AIModelService:
    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[AIModel]:
        result = await db.execute(select(AIModel).offset(skip).limit(limit))
        return result.scalars().all()

    async def get(self, db: AsyncSession, model_id: int) -> Optional[AIModel]:
        result = await db.execute(select(AIModel).where(AIModel.id == model_id))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, obj_in: AIModelCreate) -> AIModel:
        db_obj = AIModel(
            name=obj_in.name,
            base_url=obj_in.base_url,
            api_key=obj_in.api_key,
            model_identifier=obj_in.model_identifier,
            is_default=obj_in.is_default,
            is_active=obj_in.is_active
        )
        # If this is set as default, unset others
        if db_obj.is_default:
            await db.execute(update(AIModel).values(is_default=False))
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, db_obj: AIModel, obj_in: AIModelUpdate) -> AIModel:
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # If setting this as default, unset others
        if update_data.get("is_default"):
            await db.execute(update(AIModel).where(AIModel.id != db_obj.id).values(is_default=False))
            
        for field in update_data:
            setattr(db_obj, field, update_data[field])
            
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, model_id: int) -> Optional[AIModel]:
        db_obj = await self.get(db, model_id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj

    async def get_default(self, db: AsyncSession) -> Optional[AIModel]:
        result = await db.execute(select(AIModel).where(AIModel.is_default == True, AIModel.is_active == True))
        return result.scalar_one_or_none()

ai_model_service = AIModelService()
