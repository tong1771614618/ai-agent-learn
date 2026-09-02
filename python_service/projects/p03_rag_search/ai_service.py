"""
==========================================================================
  AI 知识点: RAG 流程（检索增强生成）
==========================================================================

  【概念 3: RAG（Retrieval-Augmented Generation）】

  RAG = 检索（Retrieval）+ 增强（Augmented）+ 生成（Generation）

  完整流程：
  ┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────┐
  │ 用户问题 │ →   │ Embedding │ →   │ 向量检索  │ →   │Top-K│
  └─────────┘     └──────────┘     └──────────┘     └──┬──┘
                                                       │
                                                       ↓
  ┌─────────┐     ┌──────────┐     ┌──────────────────────┐
  │ 最终回答 │ ←   │   LLM    │ ←   │ 知识上下文 + 用户问题 │
  └─────────┘     └──────────┘     └──────────────────────┘

  ┌──────────────────────────────────────────────────────────────┐
  │ 对比: 项目 1/2 vs 项目 3                                    │
  ├──────────────┬───────────────────────────────────────────────┤
  │ 项目 1/2     │ LLM 靠自己的训练数据回答（可能有幻觉）        │
  │ 项目 3 (RAG) │ LLM 基于你提供的私有知识回答（更准确+可溯源） │
  └──────────────┴───────────────────────────────────────────────┘

  为什么 RAG 很重要？
  1. LLM 的训练数据有截止日期，不知道你公司的内部文档
  2. LLM 会产生幻觉（编造看似合理但错误的信息）
  3. RAG 让 LLM "开卷考试"——给它参考资料再回答

  上游：routes.py 调用 search()
  下游：返回 answer + sources → PHP → 前端展示

  【本文件的三个核心函数】
  1. init_kb()      — 建库：加载文档 → embedding → 存入向量数据库
  2. search(query)  — 查询：embedding → 向量检索 → 构建prompt → LLM生成
  3. get_logs()     — 调试：返回最近一次搜索的日志
==========================================================================
"""

import time
from typing import Optional
from python_service.shared.llm_client import client
from python_service.shared.logger import agent_log
from python_service.config import settings
from .prompts import SYSTEM_PROMPT, FALLBACK_PROMPT
from .schemas import SearchResponse, Source
from . import vector_store as vs
from . import kb_loader

log = agent_log("P03")

# ─── 最近一次搜索的日志缓存（调试用）───────────────────────────
_last_logs: list = []


def init_kb() -> dict:
    """
    初始化知识库

    流程：加载 MD 文件 → 按 Q&A 分块 → Embedding → 存入 ChromaDB
    只需执行一次，重启服务后 ChromaDB 持久化数据自动恢复。
    """
    t0 = time.time()
    log.request("初始化知识库")

    # 1. 加载知识库文件并按 Q&A 分块
    chunks = kb_loader.load_knowledge_base()
    print(f"[P03] 知识库加载完成: {len(chunks)} 个 chunks")

    if not chunks:
        log.complete(rounds=1, time_s=time.time() - t0)
        return {"status": "empty", "chunks": 0, "message": "知识库为空"}

    # 2. 存入向量数据库（ChromaDB 内置 ONNX 模型自动 embedding）
    texts = [c["text"] for c in chunks]
    metadatas = [{"source": c["source"], "category": c["category"]} for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    vs.add_documents(texts, metadatas, ids)
    print(f"[P03] 向量化完成: {len(chunks)} 个 chunks 已存入 ChromaDB")

    elapsed = time.time() - t0
    log.complete(rounds=1, time_s=elapsed)

    return {
        "status": "ok",
        "chunks": len(chunks),
        "time": round(elapsed, 2),
    }


def search(query: str, top_k: int = 3) -> SearchResponse:
    """
    RAG 搜索入口 — 项目 3 的核心函数

    流程（ChromaDB 内置 Embedding，简化为 3 步）：
    1. Vector search  — ChromaDB 自动 embedding + 相似度检索
    2. Build prompt   — 把检索到的知识注入 Prompt
    3. LLM generate   — 基于上下文生成回答
    """
    log.request(query)
    t0 = time.time()

    total_chunks = vs.get_count()
    if total_chunks == 0:
        log.complete(rounds=1, time_s=time.time() - t0)
        return SearchResponse(
            answer="知识库尚未初始化，请先调用 /p03/init-kb 初始化。",
            sources=[],
            retrieved_count=0,
            total_chunks=0,
        )

    # ─── 第 1 步: 向量检索（ChromaDB 内部自动 embedding）─────
    t_search = time.time()
    results = vs.search_similar(query, top_k=top_k)
    search_ms = (time.time() - t_search) * 1000

    # 日志: 检索结果
    top_results = [{"score": r["score"], "text": r["text"][:80]} for r in results[:3]]
    log.rag(
        query=query,
        total_chunks=total_chunks,
        retrieved=len(results),
        model="all-MiniLM-L6-v2 (ChromaDB ONNX)",
        top_results=top_results,
    )

    # ─── 第 2 步: 构建 RAG Prompt ────────────────────────────
    if results:
        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(
                f"--- 知识片段 {i} (来源: {r['source']}, 分类: {r['category']}, "
                f"相似度: {r['score']:.2f}) ---\n{r['text']}"
            )
        context = "\n\n".join(context_parts)
        system_prompt = SYSTEM_PROMPT.format(context=context)
    else:
        system_prompt = FALLBACK_PROMPT

    # ─── 第 3 步: 调用 LLM 生成回答 ─────────────────────────
    response = client.chat.completions.create(
        model=settings.QWEN_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        temperature=0.3,  # 基于知识回答，不需要太多创造性
    )

    usage = response.usage
    answer = response.choices[0].message.content

    log.llm(round=1, model=settings.QWEN_MODEL, temp=0.3, usage=usage)
    log.answer(round=1, preview=answer)

    # 构建来源列表
    sources = [
        Source(
            text=r["text"],
            source=r["source"],
            category=r["category"],
            score=r["score"],
        )
        for r in results
    ]

    # 缓存日志供 /p03/logs 查看
    global _last_logs
    _last_logs = [
        {"type": "vector_search", "duration_ms": round(search_ms, 1), "total": total_chunks, "retrieved": len(results), "model": "all-MiniLM-L6-v2 (ChromaDB ONNX)"},
        *[{"type": "source", "source": s.source, "category": s.category, "score": s.score} for s in sources],
        {"type": "llm_generate", "model": settings.QWEN_MODEL, "tokens": usage.total_tokens if usage else 0},
    ]

    log.complete(rounds=1, time_s=time.time() - t0)

    return SearchResponse(
        answer=answer,
        sources=sources,
        retrieved_count=len(results),
        total_chunks=total_chunks,
    )


def get_logs() -> list:
    """获取最近一次搜索的详细日志（前端展示用）"""
    return _last_logs
