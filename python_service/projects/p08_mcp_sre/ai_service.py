"""
==========================================================================
  AI 知识点: SRE Agent + MCP 工具调用 + Guardrails
==========================================================================

  【概念: Agent Loop with MCP Tools】

  这个 Agent 和项目 2/4 的 Agent Loop 结构类似，区别在于：
  1. 工具不是本地定义的，而是从 MCP Server 远程发现的
  2. 工具执行不是本地调用的，而是通过 MCP Client 远程执行的
  3. 增加了 Guardrails：危险工具暂停等确认

  完整的数据流：
    用户: "系统好像变慢了，帮我查一下"
      ↓
    SRE Agent: 通过 MCPClient.list_tools() 发现工具
      ↓
    LLM: 决定调用 check_system_load
      ↓
    MCPClient.call_tool("check_system_load", {}) → MCP Server (8002端口)
      ↓
    MCP Server: 执行 os.getloadavg() → 返回结果
      ↓
    LLM: 看到负载正常，继续查磁盘...
      ↓
    多轮循环后给出诊断结论

  【概念: Guardrails（安全护栏）的实现】

  与 P04 HITL 的审批机制类似，但位置不同：
  - P04: 审批在工具执行层（tools.py 的 execute_tool 里拦截）
  - P08: 审批在 Agent 层（ai_service.py 的 Agent Loop 里拦截）

  为什么 P08 在 Agent 层做？
  因为 MCP Server 不应该知道"哪个 Agent 在用我"，
  它只负责执行工具。安全策略应该由调用方（Agent）决定。

  上游：routes.py 调用 diagnose() 和 confirm_action()
  下游：通过 MCPClient 调用 MCP Server 执行运维工具
==========================================================================
"""

import json
import time
import uuid
from typing import Optional
from python_service.shared.llm_client import client
from python_service.shared.logger import agent_log
from python_service.config import settings
from .prompts import SYSTEM_PROMPT
from .mcp_client import MCPClient

log = agent_log("P08")

# ─── Guardrails: 危险工具列表 ─────────────────────────────────
# 这些工具执行前需要用户确认（与 P04 的 HITL_ACTIONS 类似）
DANGEROUS_TOOLS = {"restart_service"}

# MCP Client 实例（连接 MCP Server）
mcp_client = MCPClient("http://127.0.0.1:8002")

# 会话存储（简化版，实际项目应使用数据库）
_sessions = {}


def diagnose(user_message: str, session_id: Optional[str] = None) -> dict:
    """
    SRE 诊断入口 — Agent Loop with MCP Tools

    与项目 2 的 chat() 对比：
    - 项目 2: tools 是本地定义的 Python 函数
    - 项目 8: tools 是从 MCP Server 远程获取的

    与项目 4 的 chat() 对比：
    - 项目 4: HITL 拦截在 tools.py 里
    - 项目 8: Guardrails 拦截在 Agent Loop 里
    """
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]

    log.request(user_message)
    t0 = time.time()

    # ─── Step 1: 从 MCP Server 发现工具 ──────────────────────
    #
    # 这就是 Tool Discovery：
    # Agent 不需要预先知道有哪些工具，
    # 而是问 MCP Server "你有什么工具？"
    try:
        llm_tools = mcp_client.get_tools_for_llm()
        log.tool_decision("mcp_discovery", {"tool_count": len(llm_tools)})
    except ConnectionError as e:
        return {
            "answer": f"MCP Server 连接失败: {e}\n请确保 MCP Server 已启动 (python3 -m python_service.projects.p08_mcp_sre.mcp_server)",
            "status": "error",
            "steps": [],
            "session_id": session_id,
            "rounds": 0,
        }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    steps = []

    # ─── Step 2: Agent Loop ──────────────────────────────────
    for round_num in range(10):
        response = client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=messages,
            tools=llm_tools if llm_tools else None,
            tool_choice="auto" if llm_tools else "none",
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
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in message.tool_calls
                ],
            }
            messages.append(msg_dict)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                log.tool_decision(tool_name, tool_args)
                steps.append({"type": "tool_call", "tool": tool_name, "args": tool_args})

                # ═══════════════════════════════════════════════════
                # Guardrails: 危险工具拦截
                # ═══════════════════════════════════════════════════
                if tool_name in DANGEROUS_TOOLS:
                    _sessions[session_id] = {
                        "messages": messages,
                        "pending_tool": tool_call.id,
                        "pending_name": tool_name,
                        "pending_args": tool_args,
                    }

                    log.hitl(reason=f"Guardrails: {tool_name} 需要确认")

                    return {
                        "answer": "",
                        "status": "pending_confirmation",
                        "confirmation_request": {
                            "tool": tool_name,
                            "arguments": tool_args,
                            "reason": f"⚠ 即将执行危险操作: {tool_name}，可能导致服务中断",
                        },
                        "steps": steps,
                        "session_id": session_id,
                        "rounds": round_num + 1,
                    }
                # ═══════════════════════════════════════════════════

                # 安全工具：通过 MCP Client 远程执行
                t_tool = time.time()
                try:
                    result_data = mcp_client.call_tool(tool_name, tool_args)
                except Exception as e:
                    result_data = {"error": str(e)}

                tool_ms = (time.time() - t_tool) * 1000
                summary = str(result_data)[:80]
                log.tool_result(tool_name, tool_ms, summary)
                steps.append({"type": "tool_result", "result": result_data})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result_data, ensure_ascii=False),
                })

        else:
            log.answer(round=round_num + 1, usage=response.usage, preview=message.content)
            steps.append({"type": "answer", "content": message.content})
            log.complete(rounds=round_num + 1, time_s=time.time() - t0)

            return {
                "answer": message.content,
                "status": "answered",
                "confirmation_request": None,
                "steps": steps,
                "session_id": session_id,
                "rounds": round_num + 1,
            }

    log.complete(rounds=10, time_s=time.time() - t0)
    return {
        "answer": "诊断步骤过多，请描述更具体的问题。",
        "status": "answered",
        "confirmation_request": None,
        "steps": steps,
        "session_id": session_id,
        "rounds": 10,
    }


def confirm_action(session_id: str, confirmed: bool) -> dict:
    """
    确认危险操作 — Guardrails 的恢复入口

    与 P04 handle_approval 类似，但更简化：
    - P04 从数据库恢复对话
    - P08 从内存 _sessions 恢复（简化版）
    """
    session = _sessions.get(session_id)
    if not session:
        return {
            "answer": "会话不存在或已过期，请重新发起诊断。",
            "status": "answered",
            "steps": [],
            "session_id": session_id,
            "rounds": 0,
        }

    messages = session["messages"]
    tool_call_id = session["pending_tool"]
    tool_name = session["pending_name"]
    tool_args = session["pending_args"]

    if confirmed:
        # 用户确认 → 执行工具
        try:
            result_data = mcp_client.call_tool(tool_name, tool_args)
        except Exception as e:
            result_data = {"error": str(e)}

        log.hitl(reason=f"{tool_name} 已确认执行", resolved=True)
    else:
        # 用户拒绝 → 告诉 LLM 操作被拒绝
        result_data = {"cancelled": True, "message": "用户取消了此操作"}
        log.hitl(reason=f"{tool_name} 已被用户取消", resolved=True)

    messages.append({
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": json.dumps(result_data, ensure_ascii=False),
    })

    steps = []

    # 继续 Agent Loop
    try:
        llm_tools = mcp_client.get_tools_for_llm()
    except Exception:
        llm_tools = []

    for round_num in range(10):
        response = client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=messages,
            tools=llm_tools if llm_tools else None,
            tool_choice="auto" if llm_tools else "none",
            temperature=0.3,
        )

        message = response.choices[0].message

        if message.tool_calls:
            msg_dict = {
                "role": "assistant", "content": message.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in message.tool_calls
                ],
            }
            messages.append(msg_dict)

            for tool_call in message.tool_calls:
                tn = tool_call.function.name
                ta = json.loads(tool_call.function.arguments)
                steps.append({"type": "tool_call", "tool": tn, "args": ta})

                if tn in DANGEROUS_TOOLS:
                    return {
                        "answer": "操作仍需确认，请联系人工运维。",
                        "status": "answered",
                        "steps": steps,
                        "session_id": session_id,
                        "rounds": round_num + 1,
                    }

                try:
                    rd = mcp_client.call_tool(tn, ta)
                except Exception as e:
                    rd = {"error": str(e)}

                steps.append({"type": "tool_result", "result": rd})
                messages.append({
                    "role": "tool", "tool_call_id": tool_call.id,
                    "content": json.dumps(rd, ensure_ascii=False),
                })
        else:
            steps.append({"type": "answer", "content": message.content})
            return {
                "answer": message.content,
                "status": "answered",
                "confirmation_request": None,
                "steps": steps,
                "session_id": session_id,
                "rounds": round_num + 1,
            }

    return {
        "answer": "处理步骤过多，请简化问题。",
        "status": "answered",
        "steps": steps,
        "session_id": session_id,
        "rounds": 10,
    }
