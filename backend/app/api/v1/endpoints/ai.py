from typing import Any, Dict, List
from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel

from app.api import deps
from app.models.user import User
from app.services.ai_service import ai_service

router = APIRouter()

class GenerateRequest(BaseModel):
    prompt: str

class GenerateResponse(BaseModel):
    steps: List[Dict[str, Any]]

@router.post("/generate", response_model=GenerateResponse)
async def generate_steps(
    *,
    request: GenerateRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Generate test steps from natural language prompt.
    """
    steps = ai_service.generate_steps_from_text(request.prompt)
    return {"steps": steps}
