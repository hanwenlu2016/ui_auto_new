from app.services.base import CRUDBase
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class ProjectService(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: ProjectCreate, **kwargs) -> Project:
        # Check if project with same name exists
        result = await db.execute(select(Project).where(Project.name == obj_in.name))
        if result.scalars().first():
            raise ValueError(f"Project with name '{obj_in.name}' already exists")
        return await super().create(db, obj_in=obj_in, **kwargs)

project_service = ProjectService(Project)
