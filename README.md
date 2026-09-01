# AI Agent 学习项目

12 个递进式项目，从零开始学习 AI Agent 开发。围绕一个模拟电商系统 "DevShop" 逐步构建完整的 AI 能力。

## 技术栈

- **后端**: Laravel 13 (PHP 8.5) + MySQL 8.0
- **AI 服务**: Python FastAPI + 阿里云 Qwen (Token Plan API)
- **前端**: 单文件 HTML（每个项目一个测试页面）
- **架构**: PHP Laravel → HTTP → Python FastAPI → LLM → 结构化 JSON → MySQL

## 项目列表

| # | 项目 | 核心 AI 概念 | 状态 |
|---|------|-------------|------|
| 1 | AI 商品客服 | System Prompt, Few-shot, Structured Output, Temperature | Done |
| 2 | Tool Calling Agent | Function Calling, Tool Schema | - |
| 3 | 订单 Agent | Multi-turn, Context Window | - |
| 4 | 售后 Agent | Human-in-the-Loop (HITL) | - |
| 5 | RAG 知识库 | Embedding, Vector DB, Retrieval | - |
| 6 | RAG + Agent | Hybrid Search, Re-ranking | - |
| 7 | Text-to-SQL | NL2SQL, Schema Injection | - |
| 8 | Code Review Bot | Long Context, Code Analysis | - |
| 9 | MCP Server | Model Context Protocol | - |
| 10 | SRE Agent | Monitoring, Auto-remediation | - |
| 11 | Multi-Agent | Agent Orchestration, Delegation | - |
| 12 | DevPilot | Full-stack AI Assistant | - |

## 目录结构

```
├── app/                              # Laravel 后端
│   ├── Http/Controllers/Api/         # 按项目版本分区 (V1, V2...)
│   ├── Models/                       # 数据模型
│   └── Services/                     # AI 服务 HTTP 客户端
│
├── python_service/                   # Python AI 服务
│   ├── main.py                       # 统一入口（注册所有项目路由）
│   ├── config.py                     # 公共配置
│   ├── shared/                       # 跨项目共享模块
│   │   └── llm_client.py            # Qwen/OpenAI 客户端
│   └── projects/                     # 每个项目独立目录
│       ├── p01_product_search/       # 项目 1
│       │   ├── prompts.py           # System Prompt + Few-shot
│       │   ├── schemas.py           # Pydantic 数据模型
│       │   ├── ai_service.py        # LLM 调用逻辑
│       │   └── routes.py            # 项目路由 (/p01/*)
│       └── p02_tool_calling/         # 项目 2 (待开发)
│
├── public/demo/                      # 前端测试页面
│   └── project1.html                 # 每个项目一个页面
│
├── docs/                             # 学习笔记（与 Obsidian 同步）
│   └── 01_AI商品客服.md
│
├── routes/api.php                    # Laravel API 路由
└── database/                         # 迁移和数据填充
```

## 本地运行

```bash
# 1. 启动 MySQL（已配置 ai_agent_learn 数据库）

# 2. 启动 Laravel
php artisan serve --port=8000
# 或通过 Nginx: dev.ai-agent-learn.com

# 3. 启动 Python AI 服务
cd ai-agent-learn
python3 -m uvicorn python_service.main:app --host 127.0.0.1 --port 8001 --reload

# 4. 打开浏览器
open http://dev.ai-agent-learn.com/demo/project1.html
```

## 环境变量

复制 `.env.example` 为 `.env`，填入你的 Qwen API Key：

```
QWEN_API_KEY=sk-sp-xxx
QWEN_MODEL=qwen3.7-plus
QWEN_BASE_URL=https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
AI_SERVICE_URL=http://127.0.0.1:8001
```

## 开发规则

1. **代码复用**: 改不重写，新项目基于已有代码扩展
2. **AI 知识注释**: 每个 AI 概念在代码中详细注释，标注上下游数据流
3. **学习笔记**: 每个项目完成后产出工作流程总结 + 课堂作业
4. **网页测试**: 用 HTML 页面测试，不用 curl
