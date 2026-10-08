"""
==========================================================================
  AI 知识点: MCP (Model Context Protocol) 协议
==========================================================================

  【概念 1: 什么是 MCP？】

  MCP = Model Context Protocol（模型上下文协议）
  由 Anthropic 在 2024 年提出的开放标准，解决一个问题：
  "如何让 AI 模型统一调用各种不同的外部工具？"

  没有 MCP 之前：
    你的 Agent 调 MySQL 要写一套代码
    调 Slack API 要写另一套代码
    调 GitHub API 又要写一套
    每个 AI 框架（LangChain / AutoGen / ...）的工具格式还不一样

  有了 MCP 之后：
    所有工具都通过统一协议暴露
    任何 MCP Client（AI 框架）都能调任何 MCP Server（工具）
    就像 HTTP 统一了 Web 通信一样

  【概念 2: MCP 的架构】

  ┌─────────────────────┐     JSON-RPC 2.0     ┌─────────────────────┐
  │   MCP Client        │ ◄──────────────────► │   MCP Server        │
  │   (你的 Agent)       │     HTTP/SSE/stdio   │   (工具提供方)        │
  │                     │                      │                     │
  │  - 发起 tool/list   │                      │  - 声明有哪些工具     │
  │  - 发起 tool/call   │                      │  - 执行工具逻辑       │
  │  - 解析返回结果       │                      │  - 返回执行结果       │
  └─────────────────────┘                      └─────────────────────┘

  【概念 3: JSON-RPC 2.0】

  MCP 底层使用 JSON-RPC 2.0 协议（一种轻量级远程调用标准）：

  请求：{"jsonrpc": "2.0", "method": "tools/list", "id": 1}
  响应：{"jsonrpc": "2.0", "result": {"tools": [...]}, "id": 1}

  两个核心方法：
  1. tools/list — 发现 Server 提供的所有工具（Tool Discovery）
  2. tools/call — 调用指定工具（Tool Execution）

  【概念 4: 为什么这个项目需要 MCP？】

  DevShop 的 SRE 运维场景：
  - 监控指标来自不同系统（MySQL、磁盘、进程）
  - 修复操作分散在不同地方（重启服务、清理日志）
  - 用 MCP 统一封装后，Agent 可以自动发现和使用所有运维工具

  本项目实现：
  - mcp_server.py = MCP Server（独立进程，8002 端口）
  - mcp_client.py = MCP Client（被 SRE Agent 调用）
  - ai_service.py = SRE Agent（调用 MCP Client 获取/使用工具）

  上游：SRE Agent 通过 mcp_client 与 MCP Server 通信
  下游：MCP Server 执行实际的运维操作（查磁盘、读日志、重启服务）
==========================================================================
"""

import json
import os
import shutil
import subprocess
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler

# ─── MCP 工具定义 ─────────────────────────────────────────────
#
# 这是 MCP Server 的核心：声明自己提供哪些工具。
# 格式遵循 OpenAI Function Calling 标准（MCP 也兼容这个格式）。
#
# 每个工具包含：
# - name: 工具名称（唯一标识）
# - description: 工具描述（LLM 据此决定何时调用）
# - parameters: 参数定义（JSON Schema 格式）

TOOLS = [
    {
        "name": "check_disk_usage",
        "description": "检查磁盘使用情况。返回各分区的总空间、已用空间、可用空间和使用率百分比。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要检查的路径，默认 /",
                }
            },
        },
    },
    {
        "name": "check_system_load",
        "description": "检查系统负载情况。返回 CPU 负载（1/5/15分钟）、内存使用率、进程数。",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "check_process",
        "description": "检查指定进程是否在运行，以及其资源占用情况。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "进程名称关键词（如 nginx, python, mysql）",
                }
            },
            "required": ["name"],
        },
    },
    {
        "name": "read_logs",
        "description": "读取指定日志文件的最后 N 行。用于排查服务异常。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "日志文件路径",
                },
                "lines": {
                    "type": "number",
                    "description": "读取最后几行，默认 50",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "check_mysql",
        "description": "检查 MySQL 数据库连接状态和基本信息。",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "restart_service",
        "description": "⚠ 危险操作：重启指定服务。可能导致短暂的服务中断。需要人工确认。",
        "parameters": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "服务名称（如 nginx, php-fpm）",
                }
            },
            "required": ["service_name"],
        },
    },
]


# ─── 工具执行逻辑 ─────────────────────────────────────────────

def execute_tool(name: str, arguments: dict) -> dict:
    """执行 MCP 工具并返回结果"""

    if name == "check_disk_usage":
        return _check_disk(arguments.get("path", "/"))
    elif name == "check_system_load":
        return _check_load()
    elif name == "check_process":
        return _check_process(arguments["name"])
    elif name == "read_logs":
        return _read_logs(arguments["file_path"], arguments.get("lines", 50))
    elif name == "check_mysql":
        return _check_mysql()
    elif name == "restart_service":
        return _restart_service(arguments["service_name"])
    else:
        return {"error": f"未知工具: {name}"}


def _check_disk(path: str) -> dict:
    """检查磁盘使用"""
    try:
        usage = shutil.disk_usage(path)
        return {
            "path": path,
            "total_gb": round(usage.total / (1024**3), 1),
            "used_gb": round(usage.used / (1024**3), 1),
            "free_gb": round(usage.free / (1024**3), 1),
            "usage_percent": round(usage.used / usage.total * 100, 1),
        }
    except Exception as e:
        return {"error": str(e)}


def _check_load() -> dict:
    """检查系统负载"""
    try:
        load1, load5, load15 = os.getloadavg()
        # 读内存信息 (macOS)
        mem_info = {}
        try:
            result = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "Pages free" in line:
                    mem_info["free_pages"] = int(line.split(":")[1].strip().rstrip("."))
                elif "Pages active" in line:
                    mem_info["active_pages"] = int(line.split(":")[1].strip().rstrip("."))
        except Exception:
            pass

        # 进程数
        try:
            result = subprocess.run(
                ["ps", "aux"], capture_output=True, text=True, timeout=5
            )
            process_count = len(result.stdout.strip().split("\n")) - 1
        except Exception:
            process_count = -1

        return {
            "cpu_load_1m": round(load1, 2),
            "cpu_load_5m": round(load5, 2),
            "cpu_load_15m": round(load15, 2),
            "process_count": process_count,
            "memory_pages": mem_info,
        }
    except Exception as e:
        return {"error": str(e)}


def _check_process(name: str) -> dict:
    """检查进程状态"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", name], capture_output=True, text=True, timeout=5
        )
        pids = result.stdout.strip().split("\n") if result.stdout.strip() else []

        if not pids or pids == [""]:
            return {"name": name, "running": False, "pid_count": 0}

        # 获取进程详细信息
        processes = []
        for pid in pids[:5]:  # 最多显示 5 个
            try:
                ps_result = subprocess.run(
                    ["ps", "-p", pid, "-o", "pid,pcpu,pmem,command"],
                    capture_output=True, text=True, timeout=5,
                )
                lines = ps_result.stdout.strip().split("\n")
                if len(lines) > 1:
                    processes.append(lines[1].strip())
            except Exception:
                pass

        return {
            "name": name,
            "running": True,
            "pid_count": len(pids),
            "processes": processes,
        }
    except Exception as e:
        return {"error": str(e)}


def _read_logs(file_path: str, lines: int) -> dict:
    """读取日志文件"""
    try:
        if not os.path.exists(file_path):
            return {"error": f"文件不存在: {file_path}"}

        # 安全检查：只允许读取日志文件
        if not file_path.endswith((".log", ".txt", ".out")):
            return {"error": "安全限制：只允许读取 .log/.txt/.out 文件"}

        result = subprocess.run(
            ["tail", "-n", str(lines), file_path],
            capture_output=True, text=True, timeout=10,
        )
        log_content = result.stdout
        line_count = len(log_content.strip().split("\n")) if log_content.strip() else 0

        return {
            "file": file_path,
            "lines_read": line_count,
            "content": log_content[-3000:],  # 限制返回长度
        }
    except Exception as e:
        return {"error": str(e)}


def _check_mysql() -> dict:
    """检查 MySQL 状态"""
    import pymysql
    from python_service.config import settings

    try:
        conn = pymysql.connect(
            host=settings.DB_HOST, port=settings.DB_PORT,
            user=settings.DB_USERNAME, password=settings.DB_PASSWORD,
            database=settings.DB_DATABASE, charset="utf8mb4",
            connect_timeout=5,
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s",
                         (settings.DB_DATABASE,))
            table_count = cursor.fetchone()[0]

            cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
            threads = cursor.fetchone()

        conn.close()
        return {
            "status": "connected",
            "version": version,
            "database": settings.DB_DATABASE,
            "table_count": table_count,
            "connected_threads": int(threads[1]) if threads else 0,
        }
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


def _restart_service(service_name: str) -> dict:
    """
    重启服务 — 危险操作

    在 MCP 层面不做拦截，拦截逻辑在 SRE Agent 的 Guardrails 层实现。
    MCP Server 只负责"能不能做"，Agent 负责"该不该做"。
    """
    try:
        # macOS 使用 brew services
        result = subprocess.run(
            ["brew", "services", "restart", service_name],
            capture_output=True, text=True, timeout=30,
        )
        return {
            "service": service_name,
            "action": "restarted",
            "output": result.stdout.strip() or result.stderr.strip(),
            "success": result.returncode == 0,
        }
    except Exception as e:
        return {"error": str(e)}


# ─── HTTP Handler（MCP 协议的传输层）────────────────────────────

class MCPRequestHandler(BaseHTTPRequestHandler):
    """
    MCP Server 的 HTTP 传输层

    处理 JSON-RPC 2.0 请求：
    - initialize: 握手（返回 Server 信息）
    - tools/list: 返回工具列表
    - tools/call: 执行工具并返回结果
    """

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self._send_error(-32700, "Parse error")
            return

        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id", 1)

        if method == "initialize":
            self._send_response(req_id, {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "DevShop SRE MCP Server",
                    "version": "0.1.0",
                },
                "capabilities": {"tools": {}},
            })
        elif method == "tools/list":
            self._send_response(req_id, {"tools": TOOLS})
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = execute_tool(tool_name, arguments)
            self._send_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            })
        else:
            self._send_error(-32601, f"Method not found: {method}")

    def _send_response(self, req_id, result):
        response = {"jsonrpc": "2.0", "result": result, "id": req_id}
        self._write_json(response)

    def _send_error(self, code, message):
        response = {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": None}
        self._write_json(response)

    def _write_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """静默日志"""
        pass


def run_server(port=8002):
    """启动 MCP Server"""
    server = HTTPServer(("127.0.0.1", port), MCPRequestHandler)
    print(f"MCP Server running on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
