"""
==========================================================================
  AI 知识点: Agent Loop + ReAct 模式
==========================================================================

  【概念 3: Agent Loop（Agent 循环）】

  项目 1 的 LLM 调用是"一次性"的：
    messages = [system, user] → LLM → 返回 JSON → 结束

  项目 2 引入 Agent Loop：
    while True:
        response = LLM(messages)
        if response 包含 tool_calls:
            执行工具 → 把结果加入 messages → 继续循环
        else:
            返回最终回答 → 结束

  这就是 Agent 和普通 LLM 调用的根本区别：
  Agent = LLM + 工具 + 循环

  【概念 4: ReAct 模式（Reasoning + Acting）】

  Agent 的工作模式叫 ReAct：
  - Reasoning（推理）: LLM 分析用户需求，决定下一步
  - Acting（行动）:   调用工具执行操作
  - 观察结果:         看工具返回了什么
  - 再推理:           根据结果决定是继续还是结束

  在本项目中：
  1. 用户: "推荐500以内的篮球鞋"
  2. LLM 推理: 需要搜索商品 → 调用 search_products(category="basketball", max_price=500)
  3. 工具执行: 查到 3 双鞋
  4. LLM 观察: 3 双鞋的详细信息
  5. LLM 推理: 信息够了 → 生成最终回答

  【概念 5: tool_calls 和 role:tool】

  LLM 调用工具时的消息格式：

  messages = [
    {"role": "system",  "content": "你是一个Agent..."},
    {"role": "user",    "content": "推荐500以内的篮球鞋"},
    {"role": "assistant","content": null, "tool_calls": [...]},  ← LLM 决定调用工具
    {"role": "tool",    "content": "{搜索结果}", "tool_call_id": "xxx"},  ← 工具返回结果
    {"role": "assistant","content": "我找到了3双..."},  ← LLM 最终回答
  ]

  关键：role=tool 的消息必须带 tool_call_id，告诉 LLM 这是哪个工具的返回。

  上游：routes.py 调用 chat()
  下游：tools.py 的 execute_tool() 被本文件的循环调用
==========================================================================
"""

import json
import time
from python_service.shared.llm_client import client
from python_service.shared.logger import agent_log
from python_service.config import settings
from .prompts import SYSTEM_PROMPT
from .tools import TOOLS, execute_tool

log = agent_log("P02")


def chat(user_message: str) -> dict:
    """
    Agent 聊天入口 — 项目 2 的核心函数

    执行 Agent Loop:
    1. 把用户消息发给 LLM（附带可用工具列表）
    2. 如果 LLM 要调用工具 → 执行 → 把结果喂回去 → 重复
    3. 如果 LLM 给出最终回答 → 返回

    返回格式:
    {
        "answer": "最终回答文本",
        "steps": [  # 每一步的记录（前端展示用）
            {"type": "tool_call", "tool": "search_products", "args": {...}},
            {"type": "tool_result", "total": 3, "products": [...]},
            {"type": "answer", "content": "..."}
        ]
    }
    """
    # ─── 日志: 请求开始 ──────────────────────────────────────
    log.request(user_message)
    t0 = time.time()

    # ─── 初始化消息列表 ─────────────────────────────────────
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    steps = []  # 记录每一步，供前端展示

    # ─── Agent Loop ─────────────────────────────────────────
    # 最多循环 5 次，防止无限循环（LLM 可能出错一直调工具）
    for round_num in range(10):
        response = client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=messages,
            tools=TOOLS,            # ← 关键：告诉 LLM 有哪些工具可用
            tool_choice="auto",     # ← auto = LLM 自己决定是否调用工具
            temperature=0.3,        # ← 比项目 1 的 0.1 稍高，Agent 需要一点灵活性
        )

        message = response.choices[0].message

        # ─── 情况 1: LLM 要调用工具 ──────────────────────────
        if message.tool_calls:
            # 日志: 本轮 LLM 决策（调工具）
            log.llm(round=round_num + 1, model=settings.QWEN_MODEL, temp=0.3,
                    usage=response.usage, decision="tool")

            # 先把 assistant 的回复（包含 tool_calls）加入消息历史
            messages.append(message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                # 日志: 工具调用决策
                log.tool_decision(tool_name, tool_args)

                steps.append({
                    "type": "tool_call",
                    "tool": tool_name,
                    "args": tool_args,
                })

                # 执行工具（计时）
                t_tool = time.time()
                result_json = execute_tool(tool_name, tool_args)
                tool_ms = (time.time() - t_tool) * 1000

                result_data = json.loads(result_json)

                # 日志: 工具执行结果
                total = result_data.get("total", 0)
                products = result_data.get("products", [])
                preview = [{"name": p.get("name"), "price": p.get("price")} for p in products[:3]]
                log.tool_result(tool_name, tool_ms, f"{total} 件商品", preview)

                steps.append({
                    "type": "tool_result",
                    "result": result_data,
                })

                # 把工具结果加入消息历史（role=tool，必须带 tool_call_id）
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_json,
                })

            # 继续循环，让 LLM 看到工具结果后决定下一步

        # ─── 情况 2: LLM 给出最终回答 ──────────────────────────
        else:
            # 日志: 最终回答
            log.answer(round=round_num + 1, usage=response.usage, preview=message.content)

            steps.append({
                "type": "answer",
                "content": message.content,
            })

            # 日志: 请求完成
            log.complete(rounds=round_num + 1, time_s=time.time() - t0)

            return {
                "answer": message.content,
                "steps": steps,
                "rounds": round_num + 1,  # 循环了几轮
            }

    # 超过最大轮数，强制结束
    log.complete(rounds=5, time_s=time.time() - t0)

    return {
        "answer": "抱歉，我处理了太多步骤，请简化你的问题重试。",
        "steps": steps,
        "rounds": 5,
    }
