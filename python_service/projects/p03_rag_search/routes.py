"""
项目 3: AI 搜索引擎 (RAG) — FastAPI 路由
"""

from fastapi import APIRouter, HTTPException
from .schemas import SearchRequest, SearchResponse
from . import ai_service

router = APIRouter(
    prefix="/p03",
    tags=["项目3: AI搜索引擎 (RAG)"],
)


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest):
    """
    RAG 搜索接口

    与项目 1/2 的区别：
    - 项目 1: /p01/parse-query → 意图解析（结构化 JSON）
    - 项目 2: /p02/chat → Agent 对话（Tool Calling）
    - 项目 3: /p03/search → RAG 搜索（检索 + 生成）
    """
    try:
        result = ai_service.search(request.query)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"RAG 搜索失败: {str(e)}")


@router.post("/init-kb")
async def init_kb_endpoint():
    """
    初始化知识库

    读取本地 MD 文件 → 按 Q&A 分块 → Embedding → 存入 ChromaDB
    只需调用一次，ChromaDB 持久化后重启不丢失
    """
    try:
        result = ai_service.init_kb()
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"知识库初始化失败: {str(e)}")


@router.get("/logs")
async def logs_endpoint():
    """获取最近一次搜索的详细日志"""
    return {"logs": ai_service.get_logs()}
