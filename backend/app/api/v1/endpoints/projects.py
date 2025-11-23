from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.user import User
from app.schemas.project import Project as ProjectSchema, ProjectCreate, ProjectUpdate
from app.services.project_service import project_service

router = APIRouter()

@router.get("/", response_model=List[ProjectSchema])
async def read_projects(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve projects.
    """
    projects = await project_service.get_multi(db, skip=skip, limit=limit)
    return projects

@router.post("/", response_model=ProjectSchema)
async def create_project(
    *,
    db: AsyncSession = Depends(deps.get_db),
    project_in: ProjectCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new project.
    """
    project = await project_service.create(db, obj_in=project_in, owner_id=current_user.id)
    return project

@router.get("/{project_id}", response_model=ProjectSchema)
async def read_project(
    *,
    db: AsyncSession = Depends(deps.get_db),
    project_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get project by ID.
    """
    project = await project_service.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectSchema)
async def update_project(
    *,
    db: AsyncSession = Depends(deps.get_db),
    project_id: int,
    project_in: ProjectUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update project.
    """
    project = await project_service.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = await project_service.update(db, db_obj=project, obj_in=project_in)
    return project

@router.delete("/{project_id}", response_model=ProjectSchema)
async def delete_project(
    *,
    db: AsyncSession = Depends(deps.get_db),
    project_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete project.
    """
    project = await project_service.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    await project_service.remove(db, id=project_id)
    return project
