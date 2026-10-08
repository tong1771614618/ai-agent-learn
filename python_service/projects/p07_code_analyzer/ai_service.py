"""
==========================================================================
  AI 知识点: Streaming（流式输出 / Server-Sent Events）
==========================================================================

  【概念 1: 为什么需要 Streaming？】

  前面所有项目都是"等 LLM 生成完毕 → 一次性返回"：
    用户等待 5 秒 → 突然收到完整回答

  Streaming 是"边生成边返回"：
    用户等待 0.5 秒 → 看到文字一个一个蹦出来 → 3 秒后生成完毕

  在代码审查场景下特别有用：
  - 分析报告通常 500-2000 字
  - 一次性返回要等 5-10 秒（用户以为卡了）
  - Streaming 让用户 0.5 秒就看到第一行，体验完全不同

  【概念 2: SSE（Server-Sent Events）】

  Streaming 的技术实现是 SSE：
  - 普通 HTTP: 客户端发请求 → 服务器返回一个完整响应 → 断开
  - SSE: 客户端发请求 → 服务器持续推送数据片段 → 直到发 [DONE] → 断开

  SSE 的数据格式（HTTP 响应体）：
    data: 第一行文字\n\n
    data: 第二行文字\n\n
    data: [DONE]\n\n

  FastAPI 通过 StreamingResponse + async generator 实现 SSE。
  OpenAI SDK 通过 stream=True 参数返回 chunk 迭代器。

  【概念 3: LLM Streaming 的工作原理】

  非流式（前面所有项目）：
    response = client.chat.completions.create(messages=...)
    answer = response.choices[0].message.content  # 等完才有内容

  流式（本项目）：
    stream = client.chat.completions.create(messages=..., stream=True)
    for chunk in stream:
        delta = chunk.choices[0].delta  # 每次只拿到一小段新增内容
        if delta.content:
            yield delta.content         # 立即推送给前端

  每个 chunk 只包含 LLM 新生成的几个字（delta），不是完整回答。
  前端把所有 delta 拼在一起就是完整回答。

  上游：routes.py 调用 review_stream() 获取 generator
  下游：FastAPI 的 StreamingResponse 把 generator 的 yield 逐个推给前端
==========================================================================
"""

import time
from typing import Optional, Generator
from python_service.shared.llm_client import client
from python_service.shared.logger import agent_log
from python_service.config import settings
from .prompts import SYSTEM_PROMPT

log = agent_log("P07")


def review_stream(
    code: str,
    language: Optional[str] = None,
    focus: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    流式代码审查 — 项目 7 的核心函数

    与前面项目的 chat() 的区别：
    1. 不用 for 循环和 Agent Loop（代码审查不需要多轮工具调用）
    2. 使用 stream=True 让 LLM 边生成边返回
    3. 返回值是 Generator（yield），不是 dict

    返回值是一个 Python Generator：
    - 每次 yield 产生一小段文本（LLM 新生成的几个字）
    - FastAPI 的 StreamingResponse 把每个 yield 的值推给前端
    - 前端通过 EventSource 实时接收并显示
    """
    t0 = time.time()
    log.request(f"代码审查请求 ({language or '自动检测'}, {len(code)} 字符)")

    # ─── 构建用户消息 ──────────────────────────────────────────
    user_message = f"请审查以下代码：\n\n"

    if language:
        user_message += f"编程语言：{language}\n\n"
    if focus:
        focus_map = {
            "security": "请重点关注安全问题（SQL注入、XSS、权限等）",
            "performance": "请重点关注性能问题（N+1查询、内存、循环等）",
            "style": "请重点关注代码规范和可维护性",
        }
        user_message += f"{focus_map.get(focus, '')}\n\n"

    user_message += f"```{language or ''}\n{code}\n```"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # ─── 流式调用 LLM ──────────────────────────────────────────
    #
    # stream=True 是 Streaming 的关键：
    # - 非流式：create() 等到 LLM 生成完毕才返回（可能要等 5-10 秒）
    # - 流式：create(stream=True) 立即返回一个迭代器，边生成边给 chunk
    #
    # 每个 chunk 的结构：
    #   chunk.choices[0].delta.content = "新生成的几个字"
    #   （注意是 delta 不是 message，delta 只包含增量内容）
    stream = client.chat.completions.create(
        model=settings.QWEN_MODEL,
        messages=messages,
        temperature=0.3,
        stream=True,
    )

    total_chars = 0

    for chunk in stream:
        # 某些 chunk 可能为空（如首个 chunk 只含元数据），需防御性检查
        if not chunk.choices:
            continue
        # 每个 chunk 包含 LLM 新生成的一小段文本
        delta = chunk.choices[0].delta
        if delta.content:
            total_chars += len(delta.content)
            # yield 把这段文本立即推给 FastAPI → 前端
            yield delta.content

    elapsed = time.time() - t0
    log.complete(rounds=1, time_s=elapsed)
    log.answer(round=1, usage=None, preview=f"[streaming] {total_chars} chars in {elapsed:.1f}s")


def review(code: str, language: Optional[str] = None, focus: Optional[str] = None) -> dict:
    """
    非流式代码审查 — 用于不需要 SSE 的场景（如 API 调用）

    内部复用 review_stream()，只是把所有 chunk 拼成完整字符串。
    这样一套逻辑两种用法：
    - /p07/review-stream → 流式（前端用 EventSource）
    - /p07/review → 非流式（PHP/Laravel 用普通 HTTP POST）
    """
    chunks = list(review_stream(code, language, focus))
    full_text = "".join(chunks)
    return {"review": full_text}
