"""
==========================================================================
  AI 知识点: HITL Agent Loop（人机协作循环）
==========================================================================

  【概念 1: Human-in-the-Loop（人机协作）】

  项目 2 的 Agent Loop 是一个"全自主"循环：
    while True:
        LLM 决定 → 执行工具 → 看结果 → 继续或结束

  项目 4 加入 HITL（Human-in-the-Loop）后变成：
    while True:
        LLM 决定 → 执行工具
        ├── 安全操作 → 结果返回 LLM → 继续循环
        ├── 危险操作 → 返回 pending_approval → ⚡ 中断循环！
        └── LLM 给出最终回答 → 结束

  HITL 的核心代码就是那个"中断循环"的判断：
    if result.get("pending_approval"):
        save_conversation()   # 保存对话状态
        return approval_req  # 返回审批请求给前端

  【概念 2: 对话状态持久化（Conversation State）】

  HITL 要求对话能够"暂停→恢复"：
  1. Agent 提出审批请求 → 保存完整 messages 到数据库
  2. 用户批准/拒绝 → 从数据库恢复 messages → 继续 Agent Loop

  这就像游戏的存档/读档：
  - 存档：Agent Loop 中断时，把 messages 存入 conversation_sessions 表
  - 读档：用户做出审批决定时，从表里恢复 messages，注入审批结果继续

  【概念 3: 审批门控（Approval Gate）】

  审批门控的位置在工具执行之后、LLM 看到结果之前：

    LLM 调用工具 → 执行工具 → 【审批门控】→ 结果返回 LLM
                                  │
                                  ├── 安全操作：直接通过
                                  └── 危险操作：等人工批准
                                        ├── 批准 → 执行操作 → 结果返回 LLM
                                        └── 拒绝 → 告诉 LLM 被拒 → LLM 重新思考

  上游：routes.py 调用 chat() 和 handle_approval()
  下游：返回的结果通过 PHP → 前端展示
==========================================================================
"""

import json
import time
import uuid
import pymysql
from typing import Optional, Dict, List
from python_service.shared.llm_client import client
from python_service.shared.logger import agent_log
from python_service.config import settings
from .prompts import SYSTEM_PROMPT
from .schemas import ChatResponse, ApprovalAction
from .tools import TOOLS, execute_tool, HITL_ACTIONS

log = agent_log("P04")


def chat(user_message: str, session_id: Optional[str] = None) -> dict:
    """
    售后 Agent 聊天入口 — 项目 4 的核心函数

    与项目 2 的 chat() 的区别：
    1. 检测工具返回中的 pending_approval 标记
    2. 检测到后中断循环，保存对话状态，返回审批请求
    3. 支持 session_id 用于对话状态持久化
    """
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]

    log.request(user_message)
    t0 = time.time()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    steps = []

    # ─── Agent Loop（与项目 2 类似，但增加了 HITL 中断检测）─────
    for round_num in range(10):
        response = client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )

        message = response.choices[0].message

        # ─── 情况 1: LLM 要调用工具 ──────────────────────────
        if message.tool_calls:
            log.llm(round=round_num + 1, model=settings.QWEN_MODEL, temp=0.3,
                    usage=response.usage, decision="tool")

            # 转为 dict 以便后续 JSON 序列化保存到数据库
            msg_dict = {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
            messages.append(msg_dict)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                log.tool_decision(tool_name, tool_args)

                steps.append({"type": "tool_call", "tool": tool_name, "args": tool_args})

                t_tool = time.time()
                result_json = execute_tool(tool_name, tool_args)
                tool_ms = (time.time() - t_tool) * 1000

                result_data = json.loads(result_json)

                # ═══════════════════════════════════════════════════
                # HITL 中断检测 — 项目 4 的核心新增逻辑
                # ═══════════════════════════════════════════════════
                #
                # 如果工具返回 pending_approval=True，说明这是一个
                # 高风险操作（退款/换货），需要人工确认后才能执行。
                #
                # 此时 Agent Loop 必须中断：
                # 1. 保存当前对话状态（messages）到数据库
                # 2. 把审批请求返回给前端
                # 3. 等用户做出决定后，通过 handle_approval() 恢复对话
                if result_data.get("pending_approval"):
                    _save_conversation(session_id, messages)

                    approval = _create_approval_request(
                        session_id,
                        result_data["action_type"],
                        result_data["params"],
                    )

                    log.hitl(
                        reason=f"{result_data['action_type']} — {json.dumps(result_data['params'], ensure_ascii=False)}",
                    )

                    log.complete(rounds=round_num + 1, time_s=time.time() - t0)

                    return {
                        "answer": "",
                        "status": "pending_approval",
                        "approval_request": approval,
                        "steps": steps,
                        "session_id": session_id,
                        "rounds": round_num + 1,
                    }
                # ═══════════════════════════════════════════════════

                # 安全操作：正常记录日志和结果
                summary = result_data.get("message", "") or result_data.get("product_name", "") or str(result_data)[:80]
                log.tool_result(tool_name, tool_ms, summary)

                steps.append({"type": "tool_result", "result": result_data})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_json,
                })

        # ─── 情况 2: LLM 给出最终回答 ──────────────────────────
        else:
            log.answer(round=round_num + 1, usage=response.usage, preview=message.content)

            steps.append({"type": "answer", "content": message.content})

            _save_conversation(session_id, messages)
            log.complete(rounds=round_num + 1, time_s=time.time() - t0)

            return {
                "answer": message.content,
                "status": "answered",
                "approval_request": None,
                "steps": steps,
                "session_id": session_id,
                "rounds": round_num + 1,
            }

    log.complete(rounds=10, time_s=time.time() - t0)
    return {
        "answer": "抱歉，处理步骤太多，请简化问题重试。",
        "status": "answered",
        "approval_request": None,
        "steps": steps,
        "session_id": session_id,
        "rounds": 10,
    }


def handle_approval(session_id: str, approved: bool) -> dict:
    """
    处理审批决定 — HITL 的"恢复"入口

    流程：
    1. 从数据库恢复对话消息（存档读档）
    2. 注入审批决定作为新的 user 消息
    3. 继续 Agent Loop — LLM 根据决定执行操作或重新思考
    """
    log.request(f"审批决定: {'approved' if approved else 'rejected'} (session: {session_id})")
    t0 = time.time()

    # 1. 恢复对话消息
    messages = _load_conversation(session_id)
    if not messages:
        return {
            "answer": "会话不存在或已过期，请重新发起售后请求。",
            "status": "answered",
            "approval_request": None,
            "steps": [],
            "session_id": session_id,
            "rounds": 0,
        }

    # 2. 更新审批请求状态
    _update_approval_status(session_id, "approved" if approved else "rejected")

    # 3. 注入审批决定（作为 user 消息告诉 LLM 结果）
    decision_text = (
        "用户已批准你的操作请求。请立即执行该操作，然后告诉用户处理结果。"
        if approved
        else "用户拒绝了你的操作请求。请理解用户的决定，提供替代方案或进一步询问用户的需求。"
    )
    messages.append({"role": "user", "content": f"[审批决定] {decision_text}"})

    steps = []

    # 4. 继续 Agent Loop
    for round_num in range(10):
        response = client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )

        message = response.choices[0].message

        if message.tool_calls:
            log.llm(round=round_num + 1, model=settings.QWEN_MODEL, temp=0.3,
                    usage=response.usage, decision="tool")
            msg_dict = {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
            messages.append(msg_dict)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                log.tool_decision(tool_name, tool_args)
                steps.append({"type": "tool_call", "tool": tool_name, "args": tool_args})

                t_tool = time.time()
                result_json = execute_tool(tool_name, tool_args)
                tool_ms = (time.time() - t_tool) * 1000
                result_data = json.loads(result_json)

                # 审批后的二次 HITL 检测（理论上不应发生，但做防御性处理）
                if result_data.get("pending_approval"):
                    return {
                        "answer": "操作仍需进一步审批，请联系人工客服。",
                        "status": "answered",
                        "approval_request": None,
                        "steps": steps,
                        "session_id": session_id,
                        "rounds": round_num + 1,
                    }

                summary = result_data.get("message", "") or str(result_data)[:80]
                log.tool_result(tool_name, tool_ms, summary)

                steps.append({"type": "tool_result", "result": result_data})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_json,
                })

        else:
            log.answer(round=round_num + 1, usage=response.usage, preview=message.content)
            steps.append({"type": "answer", "content": message.content})

            _save_conversation(session_id, messages)
            log.complete(rounds=round_num + 1, time_s=time.time() - t0)

            return {
                "answer": message.content,
                "status": "answered",
                "approval_request": None,
                "steps": steps,
                "session_id": session_id,
                "rounds": round_num + 1,
            }

    log.complete(rounds=10, time_s=time.time() - t0)
    return {
        "answer": "处理步骤过多，请联系人工客服。",
        "status": "answered",
        "approval_request": None,
        "steps": steps,
        "session_id": session_id,
        "rounds": 10,
    }


# ─── 辅助函数：数据库操作 ────────────────────────────────────────

def _save_conversation(session_id: str, messages: list):
    """保存对话消息到数据库（存档）"""
    conn = pymysql.connect(
        host=settings.DB_HOST, port=settings.DB_PORT,
        user=settings.DB_USERNAME, password=settings.DB_PASSWORD,
        database=settings.DB_DATABASE, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM conversation_sessions WHERE session_id = %s",
                (session_id,),
            )
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE conversation_sessions SET messages = %s WHERE session_id = %s",
                    (json.dumps(messages, ensure_ascii=False, default=str), session_id),
                )
            else:
                cursor.execute(
                    "INSERT INTO conversation_sessions (session_id, messages) VALUES (%s, %s)",
                    (session_id, json.dumps(messages, ensure_ascii=False, default=str)),
                )
        conn.commit()
    finally:
        conn.close()


def _load_conversation(session_id: str) -> Optional[list]:
    """从数据库恢复对话消息（读档）"""
    conn = pymysql.connect(
        host=settings.DB_HOST, port=settings.DB_PORT,
        user=settings.DB_USERNAME, password=settings.DB_PASSWORD,
        database=settings.DB_DATABASE, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT messages FROM conversation_sessions WHERE session_id = %s",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
    finally:
        conn.close()


def _create_approval_request(session_id: str, action_type: str, params: dict) -> dict:
    """创建审批请求记录"""
    # 从 params 中提取 reason（不同工具参数名一致）
    reason = params.get("reason", "")

    conn = pymysql.connect(
        host=settings.DB_HOST, port=settings.DB_PORT,
        user=settings.DB_USERNAME, password=settings.DB_PASSWORD,
        database=settings.DB_DATABASE, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO approval_requests
                   (session_id, action_type, action_params, reason, status)
                   VALUES (%s, %s, %s, %s, 'pending')""",
                (session_id, action_type, json.dumps(params, ensure_ascii=False), reason),
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "type": action_type,
        "params": params,
        "reason": reason,
    }


def _update_approval_status(session_id: str, status: str):
    """更新审批请求状态"""
    conn = pymysql.connect(
        host=settings.DB_HOST, port=settings.DB_PORT,
        user=settings.DB_USERNAME, password=settings.DB_PASSWORD,
        database=settings.DB_DATABASE, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE approval_requests SET status = %s
                   WHERE session_id = %s AND status = 'pending'""",
                (status, session_id),
            )
        conn.commit()
    finally:
        conn.close()
