"""
AI Agent Learn - LLM Demo
项目 1 前置：调通 Qwen API，理解 LLM 调用的基本流程

用法:
    python3 demo/01_llm_chat.py
    python3 demo/01_llm_chat.py "你好，介绍一下你自己"
"""

import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# ─── 配置 ───────────────────────────────────────────────
client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),
    base_url=os.getenv("QWEN_BASE_URL", "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"),
)

MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

# ─── 核心函数 ────────────────────────────────────────────
def chat(user_message: str, system_prompt: str = "你是一个有帮助的助手。") -> str:
    """
    最基础的 LLM 调用：
    System Prompt + User Message → LLM → 文本响应

    这就是项目 1 (AI 商品客服) 的核心：
    用户输入 → LLM 理解意图 → 返回结构化结果
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
    )

    # 理解 response 结构
    # response.choices[0].message.content  → 模型返回的文本
    # response.usage.prompt_tokens          → 输入消耗的 token 数
    # response.usage.completion_tokens      → 输出消耗的 token 数
    # response.usage.total_tokens           → 总 token 数

    usage = response.usage
    print(f"\n[Token 统计] 输入: {usage.prompt_tokens} | 输出: {usage.completion_tokens} | 总计: {usage.total_tokens}")

    return response.choices[0].message.content


def chat_stream(user_message: str, system_prompt: str = "你是一个有帮助的助手。"):
    """
    流式输出：LLM 边生成边返回，用户不用等全部生成完
    这是实际项目中几乎必用的模式（用户体验好很多）
    """
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        stream=True,
    )

    print("\n[流式输出] ", end="", flush=True)
    for chunk in stream:
        if not chunk.choices:
            continue
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()


# ─── 主程序 ──────────────────────────────────────────────
if __name__ == "__main__":
    # 检查 API Key
    if not os.getenv("QWEN_API_KEY"):
        print("错误: 请在 .env 文件中设置 QWEN_API_KEY")
        print("示例: QWEN_API_KEY=sk-xxxxxxxxxxxxxxxx")
        sys.exit(1)

    # 获取用户输入
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        message = "查询一下今天青岛市的天气"

    print(f"[模型] {MODEL}")
    print(f"[用户] {message}")

    # 普通调用
    result = chat(message)
    print(f"[AI]   {result}")

    # 流式调用
    print("\n--- 流式模式 ---")
    chat_stream(message)
