## 项目 2: AI 商品搜索 Agent — 学习笔记

### 浓缩工作流程

```
用户: "推荐500以内的篮球鞋"
    ↓
PHP: POST /api/v2/chat → Python /p02/chat
    ↓
Agent Loop 第 1 轮:
    LLM 看到 tools=[search_products]
    LLM 决定: 调用 search_products(category="basketball", max_price=500)
    ↓
Python 执行工具: pymysql → MySQL → 返回 1 件商品
    ↓
Agent Loop 第 2 轮:
    LLM 看到工具结果（1 双 Anta 篮球鞋 ¥369）
    LLM 决定: 信息够了，生成最终回答
    ↓
返回: "帮你找到了 1 款 500 元以内的篮球鞋..."
```

### 与项目 1 的核心区别

| | 项目 1 | 项目 2 |
|--|--------|--------|
| LLM 角色 | 翻译器（自然语言→JSON） | Agent（决策者） |
| LLM 输出 | 固定 JSON 格式 | 自然语言回答 |
| 谁查数据库 | PHP (Laravel) | Python (pymysql，作为工具) |
| LLM 调用次数 | 1 次 | 2+ 次（Agent Loop） |
| 核心概念 | Structured Output | Tool Calling + Agent Loop |

### 核心 AI 概念速查

| 概念 | 作用 | 本项目应用 |
|------|------|-----------|
| Function Calling | LLM 可以决定调用外部函数 | 定义 search_products 工具，LLM 自主调用 |
| Tool Schema | 告诉 LLM 工具有哪些参数 | tools.py 里的 TOOLS 列表 |
| Tool Result | 工具执行结果喂回给 LLM | messages 里加 role=tool 的消息 |
| Agent Loop | while 循环直到 LLM 不再调用工具 | ai_service.py 里的 for 循环 |
| ReAct 模式 | 推理→行动→观察→再推理 | LLM 思考→调工具→看结果→回答 |
| tool_choice | 控制 LLM 是否必须调用工具 | "auto" = LLM 自己决定 |

### 关键代码片段

**工具定义** (tools.py):
```python
TOOLS = [{
    "type": "function",
    "function": {
        "name": "search_products",
        "description": "搜索商品数据库",
        "parameters": { "type": "object", "properties": {...} }
    }
}]
```

**Agent Loop** (ai_service.py):
```python
for round_num in range(5):
    response = client.chat.completions.create(
        messages=messages,
        tools=TOOLS,          # 告诉 LLM 有工具可用
        tool_choice="auto",   # LLM 自己决定是否调用
    )
    if message.tool_calls:    # LLM 要调工具
        result = execute_tool(...)
        messages.append({"role": "tool", "content": result})
    else:                     # LLM 给出最终回答
        return message.content
```

### 课堂作业

#### 作业 1: 新增一个工具

- **目标**: 练习 Tool Schema 定义和工具执行
- **步骤**:
  1. 在 `tools.py` 的 TOOLS 列表里新增一个 `get_product_detail` 工具
  2. 参数: `product_id` (integer)
  3. 在 `execute_tool()` 里添加对应的查询逻辑
  4. 在 prompts.py 的 SYSTEM_PROMPT 里告诉 Agent 这个新工具
- **预期效果**: 对 Agent 说"帮我看看 ID 为 3 的商品详情"，Agent 会调用 get_product_detail 并返回详细信息
- **提示**: 只涉及已完成项目的概念（Tool Schema + execute_tool），不涉及新概念

#### 作业 2: 调整 tool_choice 观察行为变化

- **目标**: 理解 tool_choice 参数的作用
- **步骤**:
  1. 在 `ai_service.py` 里把 `tool_choice="auto"` 改成 `tool_choice="required"`
  2. 重启 Python 服务，发送"你好"
  3. 再改成 `tool_choice="none"`，发送"推荐500以内的篮球鞋"
- **预期效果**:
  - `"required"` → 即使打招呼也会强制调用工具（可能报错）
  - `"none"` → 即使问商品问题也不会调用工具，直接瞎编回答
- **思考**: 什么场景下应该用 `"required"` 而不是 `"auto"`？

#### 作业 3: 修改 Agent 最大循环轮数

- **目标**: 理解 Agent Loop 的边界控制
- **步骤**:
  1. 在 `ai_service.py` 里把 `for round_num in range(5)` 改成 `range(1)`
  2. 发送一个需要搜索的问题
  3. 观察 Agent 是否能在 1 轮内完成
  4. 再改成 `range(10)`，发送一个复杂问题
- **预期效果**:
  - `range(1)` → Agent 调用工具后没有机会看结果，直接返回"处理了太多步骤"
  - `range(10)` → Agent 有更多轮次可以搜索多次（但目前只有 1 个工具，所以效果不明显）
- **思考**: 为什么需要限制最大轮数？不限制会怎样？
