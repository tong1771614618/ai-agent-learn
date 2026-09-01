"""
==========================================================================
  AI 知识点: LLM 调用参数 + Token + 响应解析
==========================================================================

  【概念 4: Temperature（温度）】

  控制 LLM 输出的"随机性"。取值范围 0~2：

  ┌────────────┬─────────────────────────────────────────────┐
  │ temperature│  效果                                        │
  ├────────────┼─────────────────────────────────────────────┤
  │ 0.0 ~ 0.2  │  几乎确定性输出，适合结构化提取、分类         │
  │            │  ← 本项目用 0.1（意图解析不需要创造性）       │
  ├────────────┼─────────────────────────────────────────────┤
  │ 0.5 ~ 0.8  │  平衡创造性和一致性，适合对话、写作          │
  │            │  ← demo/01_llm_chat.py 用 0.7               │
  ├────────────┼─────────────────────────────────────────────┤
  │ 1.0 ~ 2.0  │  高度随机，适合创意写作、头脑风暴            │
  └────────────┴─────────────────────────────────────────────┘

  【概念 5: response_format（响应格式约束）】

  response_format={"type": "json_object"} 是 API 层面的强制约束：
  - 即使 System Prompt 里说了"只返回 JSON"，LLM 偶尔还是会加点废话
  - response_format 在 API 层面保证输出一定是合法 JSON
  - 这是 Prompt 约束 + API 约束的"双保险"

  【概念 6: Token（令牌）】

  LLM 不直接处理文字，而是把文字切成 token：
  - 英文：约 1 token ≈ 4 个字符 ≈ 0.75 个单词
  - 中文：约 1-2 个汉字 ≈ 1 token
  - 每次调用消耗 = prompt_tokens (输入) + completion_tokens (输出)
  - Token 消耗 = 钱！所以 Context 管理很重要（项目 5 会深入）

  【概念 7: LLM 调用生命周期】

  一次完整的 LLM 调用流程：

  messages = [system, user]
       ↓
  模型 tokenizer 编码 → tokens
       ↓
  模型推理（消耗算力/时间）
       ↓
  生成 completion tokens
       ↓
  tokenizer 解码 → 文本
       ↓
  response_format 校验（如果是 json_object）
       ↓
  返回 response 对象 {choices, usage}

  下游流程：
  prompts.py (System Prompt) → 本文件 (组装 messages + 调用)
       ↓ 拿到 JSON
  schemas.py (Pydantic 校验) → routes.py (FastAPI 返回)
       ↓ HTTP
  PHP AiService.php → ProductSearchController.php
==========================================================================
"""

from python_service.shared.llm_client import client
from python_service.config import settings
from .prompts import SYSTEM_PROMPT
from .schemas import ParsedQuery


def parse_query(query: str) -> ParsedQuery:
    """
    将用户自然语言查询解析为结构化数据

    这就是项目 1 的核心函数。
    它做的事情非常简单：接收一句话，返回一个 JSON 对象。
    但背后的意义很大——这是"让 AI 理解人类语言"的关键步骤。

    调用链：
      ProductSearchController.php
        → AiService.php (HTTP POST)
          → routes.py (FastAPI endpoint)
            → 本文件 (调 LLM)
              → 返回结构化 JSON
    """
    response = client.chat.completions.create(
        model=settings.QWEN_MODEL,      # 用哪个模型（qwen3.7-plus）

        # ─── messages: 给 LLM 的完整上下文 ──────────────────
        # messages 是一个数组，按顺序包含所有对话内容。
        # system 放最前面（设定规则），user 放后面（实际输入）。
        # 在项目 2 (Tool Calling) 中，这里还会有 assistant 和 tool 角色的消息。
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},  # ← 来自 prompts.py
            {"role": "user", "content": query},            # ← 用户实际输入
        ],

        # ─── response_format: API 层面的 JSON 约束 ───────────
        # 双保险机制：Prompt 里说了"只返回 JSON" + API 层面强制 JSON 输出。
        # 如果 LLM 试图输出非 JSON 内容，API 会报错而不是返回脏数据。
        response_format={"type": "json_object"},

        # ─── temperature: 控制输出随机性 ─────────────────────
        # 0.1 = 几乎确定性输出。
        # 意图解析是"分类任务"，不需要创造性，需要的是稳定可靠。
        # 对比：demo/01_llm_chat.py 用 0.7，因为那里是开放式对话。
        temperature=0.1,
    )

    # ─── 解析响应 ────────────────────────────────────────────
    # response 结构：
    # {
    #   "choices": [{"message": {"content": "{...json...}"}}],
    #   "usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}
    # }
    raw_json = response.choices[0].message.content

    # Token 使用统计（生产环境应该写入日志系统，后续项目会做 Observability）
    usage = response.usage
    print(f"[P01] Token: 输入={usage.prompt_tokens} 输出={usage.completion_tokens} 总计={usage.total_tokens}")

    # ─── Pydantic 校验 ──────────────────────────────────────
    # model_validate_json 做两件事：
    # 1. 解析 JSON 字符串 → Python dict
    # 2. 校验 dict 是否符合 ParsedQuery 的字段定义
    # 如果 LLM 返回了意外的字段或缺少了必填字段，这里会抛异常。
    # 这是结构化输出的最后一道防线。
    return ParsedQuery.model_validate_json(raw_json)
