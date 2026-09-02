"""
==========================================================================
  AI 知识点: Tool Schema（工具定义）
==========================================================================

  【概念 1: Function Calling / Tool Calling】

  项目 1 中，LLM 只做"意图解析"，返回一个 JSON 对象，
  然后 PHP 自己去查数据库。LLM 不关心查询结果。

  项目 2 引入 Tool Calling：LLM 可以"决定"调用哪些工具。
  你只需要告诉 LLM 有哪些工具可用（名称、参数、用途），
  LLM 会自己判断什么时候调用、传什么参数。

  这就是 Agent 和简单 LLM 调用的核心区别：
  - 项目 1: LLM 是"翻译器"（自然语言 → 结构化 JSON）
  - 项目 2: LLM 是"决策者"（决定调用什么工具、怎么组合结果）

  【概念 2: Tool Schema（工具描述格式）】

  OpenAI 标准格式（Qwen/DeepSeek 都兼容）：
  {
    "type": "function",
    "function": {
      "name": "search_products",           ← 工具名（LLM 用这个名字调用）
      "description": "搜索商品数据库",       ← 告诉 LLM 这个工具干什么
      "parameters": { ... }                 ← JSON Schema，定义参数
    }
  }

  为什么 description 很重要？
  LLM 靠 description 判断"要不要调用这个工具"。
  写得不清楚 → LLM 可能不调用或者调错工具。

  上游：ai_service.py 把 TOOLS 传给 LLM
  下游：execute_tool() 根据 LLM 的选择执行对应函数
==========================================================================
"""

import json
import pymysql
from python_service.config import settings


# ─── 工具定义（告诉 LLM 有哪些工具可用）─────────────────────────#
# 这是项目 2 的核心新增内容。
# LLM 看到这个列表后，会在需要搜索商品时主动调用 search_products。
#
# 对比项目 1：
#   项目 1 的 LLM 返回 {"intent":"search", "keywords":["跑步"]}
#   项目 2 的 LLM 返回 tool_call: search_products(keywords=["跑步"])
#
# 区别在于：项目 2 的 LLM 知道有工具可用，所以它的输出格式变了。

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "搜索商品数据库。可以根据关键词、分类、价格范围、品牌来筛选商品。返回匹配的商品列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "搜索关键词，如 ['跑步', '鞋', '夏天']"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["running", "basketball", "casual", "hiking", "training", "swimming"],
                        "description": "商品分类"
                    },
                    "max_price": {
                        "type": "number",
                        "description": "最高价格（元）"
                    },
                    "brands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "品牌名列表，如 ['Nike', 'Adidas']"
                    },
                },
                "required": []
            }
        }
    },
    {
            "type": "function",
            "function": {
                "name": "get_product_detail",
                "description": "获取商品详细信息。根据商品 ID 获取特定商品的详细信息。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "number",
                            "description": "商品 ID"
                        }
                    },
                    "required": ["product_id"]
                }
            }
        },

]


# ─── 工具执行（Python 直接查 MySQL）────────────────────────────
#
# 项目 1: PHP 查 MySQL
# 项目 2: Python 查 MySQL（作为 Agent 的"工具"）
#
# 在真实的生产环境中，工具可能是：
#   - 数据库查询
#   - HTTP API 调用
#   - 文件读写
#   - 代码执行
#   - 任何你能想到的操作

def execute_tool(tool_name: str, arguments: dict) -> str:
    """
    根据工具名和参数执行对应操作，返回 JSON 字符串

    LLM 的 tool_call 会包含 name 和 arguments，
    我们根据 name 找到对应函数，执行后把结果返回给 LLM。
    """
    if tool_name == "search_products":
        return _search_products(**arguments)
    elif tool_name == "get_product_detail":
        return _get_product_detail(**arguments) 
    else:
        return json.dumps({"error": f"未知工具: {tool_name}"})


def _search_products(
    keywords: list = None,
    category: str = None,
    max_price: float = None,
    brands: list = None,
) -> str:
    """
    直接查询 MySQL 商品表

    这是项目 2 里 Agent 的"手"——LLM 决定要搜索，这里负责实际执行。
    """
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
            sql = "SELECT id, name, brand, category, price, tags FROM products WHERE status = 1"
            params = []


            if category:
                sql += " AND category = %s"
                params.append(category)

            if max_price:
                sql += " AND price <= %s"
                params.append(max_price)

            if brands:
                placeholders = ",".join(["%s"] * len(brands))
                sql += f" AND brand IN ({placeholders})"
                params.extend(brands)

            if keywords:
                for kw in keywords:
                    sql += " AND (name LIKE %s OR description LIKE %s OR JSON_CONTAINS(tags, %s))"
                    params.extend([f"%{kw}%", f"%{kw}%", json.dumps(kw, ensure_ascii=False)])

            sql += " LIMIT 10"

            cursor.execute(sql, params)
            products = cursor.fetchall()

            # 把 Decimal 转成 float，否则 json.dumps 会报错
            for p in products:
                if 'price' in p:
                    p['price'] = float(p['price'])
                if 'tags' in p and isinstance(p['tags'], str):
                    p['tags'] = json.loads(p['tags'])

            return json.dumps({
                "total": len(products),
                "products": products,
            }, ensure_ascii=False)
    finally:
        conn.close()
def _get_product_detail(
    product_id: int = None
) -> str:
    """
    直接查询 MySQL 商品表

    这是项目 2 里 Agent 的"手"——LLM 决定要搜索，这里负责实际执行。
    """
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
            sql = "SELECT id, name, brand, category, price, tags FROM products WHERE status = 1"
            params = []

            if product_id:
                sql += " AND id = %s"
                params.append(product_id)

            sql += " LIMIT 10"

            cursor.execute(sql, params)
            products = cursor.fetchall()

            # 把 Decimal 转成 float，否则 json.dumps 会报错
            for p in products:
                if 'price' in p:
                    p['price'] = float(p['price'])
                if 'tags' in p and isinstance(p['tags'], str):
                    p['tags'] = json.loads(p['tags'])

            return json.dumps({
                "total": len(products),
                "products": products,
            }, ensure_ascii=False)
    finally:
        conn.close()