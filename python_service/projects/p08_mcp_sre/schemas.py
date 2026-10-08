"""
项目 8: MCP + SRE Agent — Pydantic 数据模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class DiagnoseRequest(BaseModel):
    """运维诊断请求"""
    message: str
    session_id: Optional[str] = None


class ConfirmAction(BaseModel):
    """确认危险操作"""
    session_id: str
    confirmed: bool
