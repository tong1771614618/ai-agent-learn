"""
项目 2 数据模型
"""

from typing import Optional, List, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """用户聊天请求"""
    message: str = Field(..., description="用户消息", max_length=1000)


class AgentStep(BaseModel):
    """Agent 执行步骤"""
    type: str = Field(..., description="步骤类型: tool_call / tool_result / answer")
    tool: Optional[str] = None
    args: Optional[dict] = None
    result: Optional[Any] = None
    content: Optional[str] = None


class ChatResponse(BaseModel):
    """Agent 聊天响应"""
    answer: str = Field(..., description="最终回答")
    steps: List[AgentStep] = Field(default_factory=list, description="执行步骤")
    rounds: int = Field(default=1, description="Agent 循环轮数")
