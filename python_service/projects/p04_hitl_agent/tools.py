"""
==========================================================================
  AI 知识点: 操作分级（Operation Classification）
==========================================================================

  【概念: 安全操作 vs 危险操作】

  在 HITL 系统中，工具（Tools）被分为两类：

  ┌──────────────────────────────────────────────────────────────────┐
  │ 安全操作（Safe）          │ 危险操作（Dangerous / HITL）       │
  ├──────────────────────────┼──────────────────────────────────────┤
  │ 查询订单（只读，无副作用） │ 退款（涉及资金，不可逆）           │
  │ 查询商品（只读）          │ 换货（涉及物流和库存）              │
  │                          │ 大额优惠券（涉及成本）              │
  ├──────────────────────────┼──────────────────────────────────────┤
  │ 立即执行，结果返回给 LLM  │ 暂停 Agent，等待人工审批           │
  └──────────────────────────┴──────────────────────────────────────┘

  为什么需要分级？
  - AI Agent 可能犯错（误解用户意图、计算错金额）
  - 涉及钱/物流的操作一旦执行就不可逆
  - 人工审批是最后一道安全防线

  本项目实现方式：
  HITL_ACTIONS 集合标记哪些工具需要审批。
  execute_tool() 检测到 HITL 操作后返回特殊的 pending_approval 标记，
  ai_service.py 的 Agent Loop 检测到此标记后中断循环。

  上游：ai_service.py 的 Agent Loop 调用 execute_tool()
  下游：pending_approval 结果导致 Agent Loop 中断，返回审批请求给前端
==========================================================================
"""

import json
import pymysql
from typing import Optional
from python_service.config import settings


# ─── HITL 操作分类 ─────────────────────────────────────────────
# 这些工具的调用不会立即执行，而是创建审批请求等待人工确认。
# 不在这个集合中的工具 = 安全操作，直接执行。
HITL_ACTIONS = {"request_refund", "request_replacement"}


# ─── 工具定义（OpenAI Function Calling 标准格式）─────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "查询订单详情。根据订单ID查询订单关联的商品信息，包括商品名称、品牌、分类、价格等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "number",
                        "description": "订单ID（即商品ID）",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_refund",
            "description": "申请退款（需要人工审批）。为用户的指定订单发起退款申请，需要提供退款金额和理由。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "number",
                        "description": "订单ID",
                    },
                    "amount": {
                        "type": "number",
                        "description": "退款金额（元）",
                    },
                    "reason": {
                        "type": "string",
                        "description": "退款原因",
                    },
                },
                "required": ["order_id", "amount", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_replacement",
            "description": "申请换货（需要人工审批）。为用户的指定订单发起换货申请。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "number",
                        "description": "订单ID",
                    },
                    "reason": {
                        "type": "string",
                        "description": "换货原因",
                    },
                },
                "required": ["order_id", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "issue_coupon",
            "description": "发放补偿优惠券。50元以内自动批准，超过50元需要人工审批。",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "补偿金额（元）",
                    },
                    "reason": {
                        "type": "string",
                        "description": "补偿原因",
                    },
                },
                "required": ["amount", "reason"],
            },
        },
    },
]


def execute_tool(tool_name: str, arguments: dict) -> str:
    """
    执行工具 — 带 HITL 审批拦截

    与项目 2 的 execute_tool 的核心区别：
    - 项目 2: 所有工具直接执行并返回结果
    - 项目 4: HITL 操作不直接执行，返回 pending_approval 标记

    这样 Agent Loop 可以检测到 pending_approval 并中断循环，
    把审批请求返回给前端等待人工确认。
    """
    # HITL 拦截：需要人工审批的操作不直接执行
    if tool_name in HITL_ACTIONS:
        return json.dumps({
            "pending_approval": True,
            "action_type": tool_name,
            "params": arguments,
        }, ensure_ascii=False)

    # 安全操作直接执行
    if tool_name == "lookup_order":
        return _lookup_order(**arguments)
    elif tool_name == "issue_coupon":
        return _issue_coupon(**arguments)
    else:
        return json.dumps({"error": f"未知工具: {tool_name}"})


def _lookup_order(order_id: int) -> str:
    """查询订单（安全操作，直接执行）"""
    conn = pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USERNAME,
        password=settings.DB_PASSWORD,
        database=settings.DB_DATABASE,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, brand, category, price FROM products WHERE id = %s",
                (order_id,),
            )
            product = cursor.fetchone()

            if not product:
                return json.dumps({"error": f"订单 {order_id} 不存在"}, ensure_ascii=False)

            product["price"] = float(product["price"])
            return json.dumps({
                "order_id": order_id,
                "product_name": product["name"],
                "brand": product["brand"],
                "category": product["category"],
                "price": product["price"],
                "status": "已签收",
            }, ensure_ascii=False)
    finally:
        conn.close()


def _issue_coupon(amount: float, reason: str) -> str:
    """
    发放优惠券 — 小额自动批准，大额走 HITL

    这个工具展示了 HITL 的动态分级：
    同一个工具根据参数值（金额大小）决定是否需要审批。
    这种模式在真实系统中很常见（如：小额转账自动、大额转账审批）。
    """
    if amount > 50:
        # 超过 50 元，需要人工审批
        return json.dumps({
            "pending_approval": True,
            "action_type": "issue_coupon",
            "params": {"amount": amount, "reason": reason},
        }, ensure_ascii=False)

    return json.dumps({
        "success": True,
        "coupon_amount": amount,
        "reason": reason,
        "message": f"已为用户发放 {amount} 元补偿优惠券",
    }, ensure_ascii=False)
