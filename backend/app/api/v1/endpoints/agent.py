"""
Agent API 端点

提供 browser-use Agent 的执行能力。
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.schemas.agent_schemas import AgentTaskRequest, AgentTaskResponse
from app.services.agent_service import agent_service
from app.core.logger import logger

router = APIRouter()


@router.post("/execute", response_model=AgentTaskResponse)
async def execute_agent_task(
    request: AgentTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    使用 browser-use Agent 执行自然语言任务 (同步等待模式)。
    """
    logger.info(f"Agent execute request | user={current_user.email} | task={request.task[:80]}")

    result = await agent_service.execute_task(
        db=db,
        task=request.task,
        model_id=request.model_id,
        headless=request.headless,
        max_steps=request.max_steps,
        use_vision=request.use_vision,
    )

    return AgentTaskResponse(**result)


@router.post("/execute_stream")
async def execute_agent_task_stream(
    request: AgentTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    使用 browser-use Agent 执行自然语言任务 (流式进度返回模式)。
    
    实时返回每一个步骤，解决长耗时请求的 Timeout 问题。
    """
    logger.info(f"Agent stream request | user={current_user.email} | task={request.task[:80]}")

    async def event_generator():
        async for item in agent_service.execute_task_stream(
            db=db,
            task=request.task,
            model_id=request.model_id,
            headless=request.headless,
            max_steps=request.max_steps,
            use_vision=request.use_vision,
        ):
            # 采用 newline-delimited JSON 格式
            yield json.dumps(item, ensure_ascii=False) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson"
    )
