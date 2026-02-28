---
name: fastapi-endpoint
description: 在本项目中创建标准的 FastAPI API 端点，包含 schema、service、router 注册，遵循项目现有架构模式。
---

# FastAPI 端点创建规范

## 项目架构说明

本项目后端位于 `backend/app/`，遵循分层架构：

```
backend/app/
├── api/v1/endpoints/   # 路由层 (Router)
├── schemas/            # 请求/响应数据模型 (Pydantic)
├── services/           # 业务逻辑层 (Service)
├── models/             # ORM 数据模型 (SQLAlchemy)
└── api/deps.py         # 依赖注入 (Auth、DB Session)
```

## 创建新端点的步骤

### 1. 在 `schemas/` 创建或更新 Schema 文件

每个资源对应一个 schema 文件，命名为 `{resource}.py`：

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ResourceBase(BaseModel):
    name: str
    description: Optional[str] = None

class ResourceCreate(ResourceBase):
    pass

class ResourceUpdate(ResourceBase):
    name: Optional[str] = None

class ResourceInDBBase(ResourceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class Resource(ResourceInDBBase):
    pass
```

### 2. 在 `services/` 创建或更新 Service 文件

Service 文件命名为 `{resource}_service.py`，继承自 `base.py` 中的基类：

```python
from app.services.base import CRUDBase
from app.models.resource import Resource
from app.schemas.resource import ResourceCreate, ResourceUpdate

class ResourceService(CRUDBase[Resource, ResourceCreate, ResourceUpdate]):
    # 添加自定义业务逻辑
    def custom_method(self, db, *, param) -> Resource:
        pass

resource_service = ResourceService(Resource)
```

### 3. 在 `api/v1/endpoints/` 创建路由文件

路由文件命名为 `{resource}.py`：

```python
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app import schemas, services

router = APIRouter()

@router.get("/", response_model=List[schemas.Resource])
async def list_resources(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """获取资源列表"""
    return await services.resource_service.get_multi(db)

@router.post("/", response_model=schemas.Resource)
async def create_resource(
    *,
    db: AsyncSession = Depends(deps.get_db),
    resource_in: schemas.ResourceCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """创建新资源"""
    return await services.resource_service.create(db, obj_in=resource_in)

@router.get("/{id}", response_model=schemas.Resource)
async def get_resource(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """获取单个资源"""
    resource = await services.resource_service.get(db, id=id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource

@router.put("/{id}", response_model=schemas.Resource)
async def update_resource(
    *,
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    resource_in: schemas.ResourceUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """更新资源"""
    resource = await services.resource_service.get(db, id=id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return await services.resource_service.update(db, db_obj=resource, obj_in=resource_in)

@router.delete("/{id}")
async def delete_resource(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """删除资源"""
    resource = await services.resource_service.get(db, id=id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    await services.resource_service.remove(db, id=id)
    return {"message": "Deleted successfully"}
```

### 4. 在 `api/v1/api.py` 注册新路由

```python
from app.api.v1.endpoints import resource

api_router.include_router(resource.router, prefix="/resources", tags=["resources"])
```

## 规范要点

- **认证**: 所有端点必须通过 `Depends(deps.get_current_user)` 进行认证
- **数据库**: 使用 `Depends(deps.get_db)` 注入异步 Session
- **错误处理**: 资源不存在时抛出 `HTTPException(status_code=404)`
- **类型注解**: 返回类型声明为 `Any`，response_model 中指定 Schema
- **命名约定**: 文件名、变量名使用小写加下划线 (snake_case)
- **注释**: 每个端点函数的 docstring 使用中文描述
