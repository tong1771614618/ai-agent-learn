"""
==========================================================================
  AI 知识点: OpenAI 客户端初始化（所有项目共用）
==========================================================================

  【为什么要抽到这里？】

  每个项目都要调 LLM，每次都要写一遍：
    client = OpenAI(api_key=..., base_url=...)

  抽到 shared/llm_client.py 后：
    - 改 API Key 只改 .env 一个地方
    - 换模型只改 .env 一个地方
    - 新项目只需 from shared.llm_client import client

  这就是软件工程里最朴素的 DRY 原则（Don't Repeat Yourself）。

  下游：
  config.py (读 .env) → 本文件 (初始化 client) → 各项目的 ai_service.py
==========================================================================
"""

from openai import OpenAI
from python_service.config import settings

# ─── 初始化 OpenAI 客户端 ─────────────────────────────────────
#
# OpenAI SDK 是 LLM 调用的标准客户端库。
# 阿里云 Qwen 提供了 OpenAI 兼容接口，所以可以直接用 openai SDK，
# 只需要把 base_url 改成 Qwen 的地址。
#
# 这就是"OpenAI 兼容"的意义：
#   不管底层是 GPT / Qwen / DeepSeek / Claude，
#   只要 API 格式兼容，代码几乎不用改。

client = OpenAI(
    api_key=settings.QWEN_API_KEY,
    base_url=settings.QWEN_BASE_URL,
)
