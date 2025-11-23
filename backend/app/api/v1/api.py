from fastapi import APIRouter
from app.api.v1.endpoints import login, users, projects, modules, pages, elements, cases, suites, execution, recording, reports

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(modules.router, prefix="/modules", tags=["modules"])
api_router.include_router(pages.router, prefix="/pages", tags=["pages"])
api_router.include_router(elements.router, prefix="/elements", tags=["elements"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(suites.router, prefix="/suites", tags=["suites"])
api_router.include_router(execution.router, prefix="/execution", tags=["execution"])
api_router.include_router(recording.router, prefix="/recording", tags=["recording"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
