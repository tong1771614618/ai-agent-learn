"""
==========================================================================
  AI 知识点: MCP Client（工具发现 + 远程调用）
==========================================================================

  【概念: MCP Client 的职责】

  MCP Client 是 Agent 和 MCP Server 之间的桥梁：
  1. 连接 MCP Server
  2. 发现 Server 提供的工具列表（tools/list）
  3. 调用工具并返回结果（tools/call）

  这与你在项目 2 里直接写 tools.py 的区别：
  - 项目 2: 工具定义和工具执行都在同一个 Python 进程里
  - 项目 8: 工具定义在 MCP Server（8002端口），Agent 通过 HTTP 远程调用

  好处是什么？
  - 工具可以独立部署（MCP Server 可以跑在另一台机器上）
  - 工具可以独立升级（更新 MCP Server 不需要改 Agent 代码）
  - 工具可以被多个 Agent 共享（一个 MCP Server 服务多个 Client）

  【概念: Tool Discovery（工具发现）】

  Agent 不需要硬编码知道有哪些工具，
  而是调用 tools/list 让 Server 告诉自己。

  这意味着：
  - 你给 MCP Server 新增一个工具 → Agent 自动就能用
  - 不需要改 Agent 代码，只需要更新 Prompt 里的工具说明

  这就是"协议"的力量：标准化后，增减工具对消费者透明。

  上游：ai_service.py 创建 MCPClient 实例，调用 list_tools / call_tool
  下游：通过 HTTP 与 mcp_server.py 通信（JSON-RPC 2.0 协议）
==========================================================================
"""

import json
import urllib.request
from typing import Optional, List, Dict


class MCPClient:
    """
    MCP Client — 连接 MCP Server 的客户端

    用法：
        client = MCPClient("http://127.0.0.1:8002")
        tools = client.list_tools()      # 发现工具
        result = client.call_tool(...)    # 调用工具
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8002"):
        self.server_url = server_url
        self._initialized = False
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send_request(self, method: str, params: dict = None) -> dict:
        """发送 JSON-RPC 2.0 请求"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._next_id(),
        }
        if params:
            payload["params"] = params

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.server_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode())
            if "error" in result:
                raise Exception(f"MCP Error: {result['error']}")
            return result.get("result", {})
        except urllib.error.URLError as e:
            raise ConnectionError(f"MCP Server 连接失败: {e}")

    def initialize(self) -> dict:
        """
        初始化握手 — MCP 协议的第一步

        Client 先告诉 Server "我是谁"，Server 返回 "我支持什么"。
        类似 HTTP 的 TLS 握手，但更简单。
        """
        result = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {
                "name": "DevShop SRE Agent",
                "version": "0.1.0",
            },
        })
        self._initialized = True
        return result

    def list_tools(self) -> List[Dict]:
        """
        工具发现 — 获取 MCP Server 提供的所有工具

        返回工具列表，格式与 OpenAI Function Calling 一致。
        Agent 拿到这个列表后可以直接传给 LLM 的 tools 参数。
        """
        if not self._initialized:
            self.initialize()
        result = self._send_request("tools/list")
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: dict = None) -> dict:
        """
        调用工具 — 通过 MCP Server 执行指定工具

        Agent 的 LLM 决定了要调什么工具、传什么参数，
        然后通过这个方法把调用请求发给 MCP Server。
        """
        if not self._initialized:
            self.initialize()
        result = self._send_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })
        # MCP 返回格式: {"content": [{"type": "text", "text": "..."}]}
        content = result.get("content", [])
        if content and content[0].get("type") == "text":
            return json.loads(content[0]["text"])
        return result

    def get_tools_for_llm(self) -> list:
        """
        把 MCP 工具列表转为 OpenAI Function Calling 格式

        MCP 的工具定义格式和 OpenAI 几乎一致，
        只需包一层 {"type": "function", "function": {...}}
        """
        tools = self.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in tools
        ]
