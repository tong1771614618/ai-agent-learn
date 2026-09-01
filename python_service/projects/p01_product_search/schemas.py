"""
数据模型定义 (Pydantic)
定义 PHP ↔ Python 之间的数据契约
"""

from typing import Optional, List, Union
from pydantic import BaseModel, Field, field_validator


def _normalize_list(v):
    """兜底：LLM 有时返回字符串或 null 而不是数组，这里统一转成 list"""
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return v


class QueryParseRequest(BaseModel):
    """PHP 发过来的请求"""
    query: str = Field(..., description="用户的自然语言查询", max_length=500)


class ParsedQuery(BaseModel):
    """LLM 解析后的结构化结果 — 这是项目 1 的核心"""
    intent: str = Field(..., description="意图: search/compare/recommend/info")
    keywords: List[str] = Field(default_factory=list, description="提取的商品关键词")
    category: Optional[str] = Field(None, description="商品类别: running/basketball/casual/hiking/training/swimming")
    budget_min: Optional[float] = Field(None, description="最低预算(元)")
    budget_max: Optional[float] = Field(None, description="最高预算(元)")
    brands: List[str] = Field(default_factory=list, description="提到的品牌")
    raw_query: str = Field(default="", description="原始用户输入(服务端填充)")
    urgency: List[str] = Field(default_factory=list, description="提到的紧急程度(如 急, 着急, 不急 等)")

    # AI 知识点: Pydantic field_validator
    # LLM 输出不可靠，即使 prompt 里要求返回数组，它偶尔也会返回字符串或 null
    # validator 是最后一道防线，确保 Python 代码拿到的数据类型一定是对的
    @field_validator('keywords', 'brands', 'urgency', mode='before')
    @classmethod
    def ensure_list(cls, v):
        return _normalize_list(v)