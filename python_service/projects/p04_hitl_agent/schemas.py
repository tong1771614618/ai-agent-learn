"""
项目 4: 售后 Agent (HITL) — Pydantic 数据模型
"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """用户聊天请求"""
    message: str
    session_id: Optional[str] = None


class ApprovalAction(BaseModel):
    """待审批的操作信息"""
    type: str                     # refund / replacement / coupon
    params: Dict[str, Any]        # 操作参数
    reason: str                   # Agent 给出的理由


class ChatResponse(BaseModel):
    """Agent 聊天响应"""
    answer: str                                              # Agent 的回答文本
    status: str                                              # answered / pending_approval
    approval_request: Optional[ApprovalAction] = None        # 待审批的操作（status=pending_approval时）
    steps: List[Dict[str, Any]] = []                         # 执行步骤记录
    session_id: Optional[str] = None
    rounds: int = 0


class ApprovalRequestModel(BaseModel):
    """审批决定请求"""
    session_id: str
    approved: bool
