import time
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.logger import logger
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

    async def test_connection(self, db_obj: AIModel) -> Dict[str, Any]:
        """
        Validate one stored model configuration by sending a lightweight chat request.
        """
        start = time.perf_counter()
        try:
            client = AsyncOpenAI(
                api_key=db_obj.api_key,
                base_url=db_obj.base_url,
                timeout=20.0,
            )
            response = await client.chat.completions.create(
                model=db_obj.model_identifier,
                messages=[{"role": "user", "content": "Reply with OK only."}],
                temperature=0,
                max_tokens=16,
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            content = (
                response.choices[0].message.content
                if response and response.choices and response.choices[0].message
                else ""
            ) or ""
            provider_message = content.strip()[:120]
            logger.info(
                "AI model connectivity test passed | model_id=%s model_name=%s latency_ms=%s",
                db_obj.id,
                db_obj.name,
                latency_ms,
            )
            return {
                "success": True,
                "model_id": db_obj.id,
                "model_name": db_obj.name,
                "latency_ms": latency_ms,
                "provider_message": provider_message,
                "error_type": None,
                "error_message": None,
            }
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            error_type, error_message = self._classify_test_error(e)
            logger.warning(
                "AI model connectivity test failed | model_id=%s model_name=%s type=%s message=%s",
                db_obj.id,
                db_obj.name,
                error_type,
                error_message,
            )
            return {
                "success": False,
                "model_id": db_obj.id,
                "model_name": db_obj.name,
                "latency_ms": latency_ms,
                "provider_message": None,
                "error_type": error_type,
                "error_message": error_message,
            }

    def _classify_test_error(self, exc: Exception) -> tuple[str, str]:
        message = str(exc).strip() or "Unknown error"
        lowered = message.lower()
        class_name = exc.__class__.__name__.lower()

        if (
            "401" in lowered
            or "403" in lowered
            or "unauthorized" in lowered
            or "invalid api key" in lowered
            or "authentication" in lowered
            or "permission" in lowered
        ):
            return "auth_error", message[:300]

        if "timeout" in lowered or "timed out" in lowered or "timeout" in class_name:
            return "timeout_error", message[:300]

        if (
            "connection" in lowered
            or "dns" in lowered
            or "network" in lowered
            or "host" in lowered
            or "socket" in lowered
            or "unreachable" in lowered
            or "refused" in lowered
        ):
            return "network_error", message[:300]

        if (
            "model" in lowered
            and ("not found" in lowered or "does not exist" in lowered or "unsupported" in lowered)
        ):
            return "model_error", message[:300]

        return "unknown_error", message[:300]

ai_model_service = AIModelService()
