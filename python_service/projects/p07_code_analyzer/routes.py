"""
==========================================================================
  AI 知识点: FastAPI StreamingResponse（流式响应）
==========================================================================

  【概念: StreamingResponse vs 普通 Response】

  普通 Response（前面所有项目用的）：
    @router.post("/chat")
    async def chat():
        result = ai_service.chat()
        return result  # 一次性返回完整 JSON

  StreamingResponse（本项目新增）：
    @router.post("/review-stream")
    async def review_stream():
        generator = ai_service.review_stream()
        return StreamingResponse(generator, media_type="text/event-stream")
        # ↑ 不是一次性返回，而是持续推送数据直到 generator 耗尽

  前端如何消费 SSE？
    方式 1: EventSource（浏览器内置 API，最简单）
      const es = new EventSource("/p07/review-stream?code=...");
      es.onmessage = (e) => { console.log(e.data); };

    方式 2: fetch + ReadableStream（POST 请求必须用这个）
      const resp = await fetch("/p07/review-stream", {method: "POST", ...});
      const reader = resp.body.getReader();
      while (true) {
          const {done, value} = await reader.read();
          // 处理每个 chunk
      }

  注意：EventSource 只支持 GET 请求。
  因为代码审查要传代码（可能很长），必须用 POST，
  所以前端用 fetch + ReadableStream 的方式消费 SSE。

  上游：前端通过 fetch POST 调用
  下游：StreamingResponse 把 ai_service 的 generator 逐 chunk 推给前端
==========================================================================
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from .schemas import CodeReviewRequest
from . import ai_service

router = APIRouter(
    prefix="/p07",
    tags=["项目7: AI代码分析器 (Streaming)"],
)


@router.post("/review")
async def review(request: CodeReviewRequest):
    """
    非流式代码审查 — 普通 HTTP 请求，等生成完一次性返回

    适用场景：
    - PHP/Laravel 后端调用（HTTP client 不支持 SSE）
    - API 集成（其他系统调你的接口）
    """
    try:
        result = ai_service.review(request.code, request.language, request.focus)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"代码审查失败: {str(e)}")


@router.post("/review-stream")
async def review_stream(request: CodeReviewRequest):
    """
    流式代码审查 — SSE (Server-Sent Events)

    与 /review 的区别：
    - /review: 等 LLM 生成完 → 返回完整 JSON（可能等 5-10 秒）
    - /review-stream: LLM 边生成边推 → 前端实时显示（0.5 秒看到第一行）

    技术细节：
    - 返回 StreamingResponse，media_type 设为 text/event-stream
    - ai_service.review_stream() 是一个 Generator，每次 yield 一小段文本
    - FastAPI 把每个 yield 的值作为 SSE 的 data: 行推送给前端
    """
    try:
        generator = ai_service.review_stream(
            request.code, request.language, request.focus
        )
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁止 Nginx 缓冲（否则流式失效）
            },
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"流式审查失败: {str(e)}")
