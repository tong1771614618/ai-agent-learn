"""
项目 1: AI 商品客服 — FastAPI 路由

路由从 main.py 拆出来，每个项目管自己的路由。
main.py 只负责注册和启动。
"""

from fastapi import APIRouter, HTTPException
from .schemas import QueryParseRequest, ParsedQuery
from .ai_service import parse_query

router = APIRouter(
    prefix="/p01",
    tags=["项目1: AI 商品客服"],
)


@router.post("/parse-query", response_model=ParsedQuery)
async def parse_query_endpoint(request: QueryParseRequest):
    """
    解析用户查询意图

    PHP 调用这个接口，把用户的自然语言转成结构化 JSON：
    "有没有适合夏天跑步的鞋？"
    → {"intent": "search", "keywords": ["跑步","鞋","夏天"], "category": "running"}
    """
    try:
        result = parse_query(request.query)
        # 回传原始查询，方便 PHP 侧调试
        result.raw_query = request.query
        return result
    except Exception as e:
        print(f"[P01 AI Service Error] {e}")
        raise HTTPException(status_code=500, detail=f"AI 解析失败: {str(e)}")
