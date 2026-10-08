"""
项目 8: MCP + SRE Agent — FastAPI 路由
"""

from fastapi import APIRouter, HTTPException
from .schemas import DiagnoseRequest, ConfirmAction
from . import ai_service

router = APIRouter(
    prefix="/p08",
    tags=["项目8: MCP+SRE Agent"],
)


@router.post("/diagnose")
async def diagnose(request: DiagnoseRequest):
    """SRE 诊断接口"""
    try:
        result = ai_service.diagnose(request.message, request.session_id)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"SRE Agent 处理失败: {str(e)}")


@router.post("/confirm")
async def confirm(request: ConfirmAction):
    """确认危险操作"""
    try:
        result = ai_service.confirm_action(request.session_id, request.confirmed)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"确认处理失败: {str(e)}")
