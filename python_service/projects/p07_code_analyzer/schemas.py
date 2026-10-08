"""
项目 7: AI 代码分析器 — Pydantic 数据模型
"""

from typing import Optional
from pydantic import BaseModel


class CodeReviewRequest(BaseModel):
    """代码审查请求"""
    code: str                              # 待审查的代码
    language: Optional[str] = None         # 编程语言（可选，自动检测）
    focus: Optional[str] = None            # 重点分析方向（security/performance/style）
