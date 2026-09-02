"""
==========================================================================
  FastAPI 统一入口 — 所有项目的 AI 服务从这里启动
==========================================================================

  启动方式：
    cd /Users/tong/ai-work/ai-agent-learn
    python3 -m uvicorn python_service.main:app --host 127.0.0.1 --port 8001 --reload

  架构：
    PHP Laravel → HTTP POST → 这里 → 各项目路由 → LLM (Qwen) → 返回给 PHP

  项目路由：
    /p01/parse-query   → 项目 1: AI 商品客服（意图解析）
    /p02/chat          → 项目 2: AI 商品搜索 Agent（Tool Calling）
    /p03/search        → 项目 3: AI 搜索引擎（RAG + Embedding）
    /p03/init-kb       → 项目 3: 知识库初始化
    ...

  新增项目只需：
    1. 在 projects/ 下创建新目录（如 p02_tool_calling/）
    2. 创建 routes.py，定义 APIRouter
    3. 在本文件中 include_router
==========================================================================
"""

from fastapi import FastAPI

app = FastAPI(
    title="AI Agent Learn - AI Service",
    description="AI Agent 学习项目统一 AI 服务（12 个项目共用）",
    version="0.3.0",
)


# ─── 健康检查（所有项目共用）──────────────────────────────────
@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "ai-service", "version": "0.3.0"}


# ─── 注册各项目路由 ───────────────────────────────────────────
# 每个项目有独立的 APIRouter，定义在自己的 routes.py 中
# prefix 在 routes.py 内部定义（如 /p01），这里不需要再加

from python_service.projects.p01_product_search.routes import router as p01_router
app.include_router(p01_router)

from python_service.projects.p02_agent.routes import router as p02_router
app.include_router(p02_router)

from python_service.projects.p03_rag_search.routes import router as p03_router
app.include_router(p03_router)

# ─── 项目 4-12 的路由会陆续添加在这里 ─────────────────────────
