"""
==========================================================================
  AI 知识点: System Prompt + Few-shot Prompting + Structured Output
==========================================================================

  【概念 1: System Prompt vs User Prompt】

  LLM 每次调用接收一组 messages，主要有三种角色：

  ┌──────────────┬─────────────────────────────────────────────┐
  │  role        │  作用                                       │
  ├──────────────┼─────────────────────────────────────────────┤
  │  system      │  设定 LLM 的身份、行为规则、输出格式         │
  │              │  LLM 会优先遵守 system 的指令                │
  │              │  用户看不到 system prompt（后端控制）         │
  ├──────────────┼─────────────────────────────────────────────┤
  │  user        │  用户的实际输入                              │
  │              │  "有没有适合夏天跑步的鞋？"                   │
  ├──────────────┼─────────────────────────────────────────────┤
  │  assistant   │  LLM 之前的回复（多轮对话时用）              │
  │              │  项目 2 会用到                               │
  └──────────────┴─────────────────────────────────────────────┘

  【概念 2: Few-shot Prompting（少样本提示）】

  在 System Prompt 里给出几个「输入→输出」的示例，
  让 LLM 理解你期望的输出格式和行为模式。

  为什么有效？LLM 本质上是"续写"——它看到你的示例后，
  会模仿同样的模式来生成新的输出。

  0 个示例 = Zero-shot (直接问)
  1-3 个示例 = Few-shot (本项目用的)
  很多示例 = Many-shot (通常不需要)

  【概念 3: Structured Output（结构化输出）】

  普通 LLM 调用返回自由文本（不可预测、不可靠）。
  结构化输出让 LLM 返回固定格式的 JSON，
  这样你的后端代码才能可靠地解析和使用结果。

  实现方式有两种（本项目都用了）：
  1. Prompt 里要求"只返回 JSON" ← 在下面的 SYSTEM_PROMPT 中
  2. API 参数 response_format={"type": "json_object"} ← 在 ai_service.py 中

  下游流程：
  System Prompt (本文件)
      ↓ 传入 LLM
  ai_service.py (调用 LLM，拿到 JSON)
      ↓ 返回给 PHP
  ProductSearchController.php (解析 JSON，查询 MySQL)
==========================================================================
"""

# ─── System Prompt ──────────────────────────────────────────────────────
#
# 这段文字是整个项目 1 的"灵魂"。
# 它决定了 LLM 如何理解自己的角色和任务。
#
# 编写技巧：
#   1. 明确身份 — "你是一个..."
#   2. 约束输出 — "你必须返回..."
#   3. 枚举可选值 — intent 只能是 search/compare/recommend/info
#   4. 给示例 — Few-shot，让 LLM 模仿格式
#   5. 强调规则 — "只返回 JSON"、"不要解释"

SYSTEM_PROMPT = """你是一个电商 AI 助手的意图解析器。
你的唯一任务是将用户的自然语言查询转换为结构化的 JSON 格式。

你必须返回一个合法的 JSON 对象，包含以下字段：
- intent: 字符串，只能是 "search"(搜索商品)、"compare"(比较商品)、"recommend"(推荐商品)、"info"(查询信息) 之一
- keywords: 字符串数组，提取出的商品关键词（产品类型、使用场景、功能特点等）
- category: 字符串或 null，商品类别，只能是: running, basketball, casual, hiking, training, swimming 之一
- budget_min: 数字或 null，最低预算（元）
- budget_max: 数字或 null，最高预算（元）
- brands: 字符串数组，提到的品牌名（如 Nike, Adidas, Asics 等）
- urgency: 字符串或 null，提到的紧急程度(如 急, 着急, 不急 等)

# ─── Few-shot 示例 ────────────────────────────────────────────
# 这 4 个示例覆盖了主要的用户输入模式：
# 示例 1: 普通搜索（无预算无品牌）
# 示例 2: 带预算约束
# 示例 3: 带品牌比较
# 示例 4: 带预算区间 + 功能需求
# 示例 5: 紧急程度

示例：
用户: "有没有适合夏天跑步的鞋？"
输出: {"intent": "search", "keywords": ["跑步", "鞋", "夏天"], "category": "running", "budget_min": null, "budget_max": null, "brands": []}

用户: "推荐500以内的篮球鞋"
输出: {"intent": "recommend", "keywords": ["篮球鞋"], "category": "basketball", "budget_min": null, "budget_max": 500, "brands": []}

用户: "Nike和Adidas哪个跑鞋好？"
输出: {"intent": "compare", "keywords": ["跑鞋"], "category": "running", "budget_min": null, "budget_max": null, "brands": ["Nike", "Adidas"]}

用户: "看看有没有防水的登山鞋，预算800到1200"
输出: {"intent": "search", "keywords": ["登山鞋", "防水"], "category": "hiking", "budget_min": 800, "budget_max": 1200, "brands": []}

用户: "急需一双跑步鞋"
输出: {"intent": "search", "keywords": ["跑步鞋"], "category": "running", "budget_min": null, "budget_max": null, "brands": [], "urgency": ["急"]}

重要规则：
1. 只返回 JSON，不要任何其他文字、解释或 markdown 标记
2. 如果用户没有提到某个字段，用 null 或空数组
3. keywords 要提取具体有意义的词，不要太笼统
4. 如果无法判断 category，设为 null"""
