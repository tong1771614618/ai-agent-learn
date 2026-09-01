"""
项目 2: AI 商品搜索 Agent — FastAPI 路由
"""

from fastapi import APIRouter, HTTPException
from .schemas import ChatRequest, ChatResponse
from .ai_service import chat

router = APIRouter(
    prefix="/p02",
    tags=["项目2: AI 商品搜索 Agent"],
)


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Agent 聊天接口

    与项目 1 的区别：
    - 项目 1: /p01/parse-query → 返回结构化 JSON（意图解析）
    - 项目 2: /p02/chat → 返回自然语言回答 + Agent 执行步骤
    """
    try:
        result = chat(request.message)
        return result
    except Exception as e:
        print(f"[P02 Agent Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent 执行失败: {str(e)}")
