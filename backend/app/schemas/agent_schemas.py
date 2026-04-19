"""
Agent 执行 Schema 定义

用于 browser-use Agent 的请求/响应数据结构。
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class AgentTaskRequest(BaseModel):
    """Agent 任务执行请求"""
    task: str
    model_id: Optional[str] = None
    headless: bool = True
    max_steps: int = 20
    use_vision: bool = False
    project_id: Optional[int] = None


class AgentStepResult(BaseModel):
    """Agent 执行后提取的单个步骤"""
    action: str
    target: str = ""
    value: str = ""
    description: str = ""
    locator_chain: Optional[Dict[str, Any]] = None


class AgentTaskResponse(BaseModel):
    """Agent 任务执行响应"""
    success: bool
    message: str
    steps: List[AgentStepResult] = []
    execution_time: float = 0.0
    total_agent_steps: int = 0
    errors: List[str] = []
