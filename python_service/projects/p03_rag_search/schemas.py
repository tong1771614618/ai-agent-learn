"""
==========================================================================
  AI 知识点: Pydantic 数据模型（RAG 搜索请求/响应）
==========================================================================

  项目 3 新增的概念：

  【Source（引用来源）】

  RAG 的一大优势是"可溯源"——AI 的回答基于哪些文档片段，
  可以明确告诉用户答案来自哪里。

  每个 Source 包含：
  - text:     原始文档片段（检索到的知识）
  - source:   来源文件名（如 "php.md"）
  - category: 知识分类（如 "PHP"、"Linux"）
  - score:    相似度分数（0~1，越高越相关）

  ┌──────────────────────────────────────────────────────────┐
  │ 对比: 项目 1/2 vs 项目 3                                │
  ├──────────────┬───────────────────────────────────────────┤
  │ 项目 1/2     │ LLM 凭空回答，不知道依据是什么            │
  │ 项目 3 (RAG) │ LLM 基于检索到的知识回答 + 标注来源       │
  └──────────────┴───────────────────────────────────────────┘

  上游：routes.py 接收请求 → 调用 ai_service.search()
  下游：返回给 PHP → 前端渲染答案 + 来源卡片
==========================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="用户问题", min_length=1)


class Source(BaseModel):
    """检索到的知识来源"""
    text: str = Field(..., description="原始文档片段")
    source: str = Field(..., description="来源文件名")
    category: str = Field(..., description="知识分类")
    score: float = Field(..., description="相似度分数")


class SearchResponse(BaseModel):
    """搜索响应"""
    answer: str = Field(..., description="AI 生成的回答")
    sources: List[Source] = Field(default_factory=list, description="引用的知识来源")
    retrieved_count: int = Field(0, description="检索到的文档数")
    total_chunks: int = Field(0, description="知识库总文档数")
