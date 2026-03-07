from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.schemas.ai_model import AIModel, AIModelCreate, AIModelUpdate, AIModelTestResponse
from app.services.ai_model_service import ai_model_service
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[AIModel])
async def read_ai_models(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    检索所有 AI 模型配置
    """
    return await ai_model_service.get_multi(db, skip=skip, limit=limit)

@router.post("/", response_model=AIModel)
async def create_ai_model(
    *,
    db: AsyncSession = Depends(deps.get_db),
    obj_in: AIModelCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    创建新的 AI 模型配置
    """
    return await ai_model_service.create(db, obj_in=obj_in)

@router.put("/{model_id}", response_model=AIModel)
async def update_ai_model(
    *,
    db: AsyncSession = Depends(deps.get_db),
    model_id: int,
    obj_in: AIModelUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    更新现有的 AI 模型配置
    """
    db_obj = await ai_model_service.get(db, model_id=model_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="AI Model not found")
    return await ai_model_service.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{model_id}", response_model=AIModel)
async def delete_ai_model(
    *,
    db: AsyncSession = Depends(deps.get_db),
    model_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    删除 AI 模型配置
    """
    db_obj = await ai_model_service.get(db, model_id=model_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="AI Model not found")
    return await ai_model_service.remove(db, model_id=model_id)


@router.post("/{model_id}/test", response_model=AIModelTestResponse)
async def test_ai_model_connection(
    *,
    db: AsyncSession = Depends(deps.get_db),
    model_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    测试指定 AI 模型配置是否可连通
    """
    db_obj = await ai_model_service.get(db, model_id=model_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="AI Model not found")

    return await ai_model_service.test_connection(db_obj)
