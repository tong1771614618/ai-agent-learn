"""
项目 4: 售后 Agent (HITL) — FastAPI 路由
"""

from fastapi import APIRouter, HTTPException
from .schemas import ChatRequest, ApprovalRequestModel
from . import ai_service

router = APIRouter(
    prefix="/p04",
    tags=["项目4: 售后Agent (HITL)"],
)


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    售后 Agent 聊天接口

    与项目 2 的区别：
    - 项目 2: /p02/chat → Agent 自主完成全部操作
    - 项目 4: /p04/chat → Agent 遇到高风险操作时暂停，返回审批请求
    """
    try:
        result = ai_service.chat(request.message, request.session_id)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"售后 Agent 处理失败: {str(e)}")


@router.post("/approve")
async def approve_endpoint(request: ApprovalRequestModel):
    """
    审批接口 — HITL 的"恢复"入口

    用户对 Agent 的操作提案做出批准/拒绝决定后调用此接口。
    Agent 会根据决定继续执行或重新思考方案。
    """
    try:
        result = ai_service.handle_approval(request.session_id, request.approved)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"审批处理失败: {str(e)}")
