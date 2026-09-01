"""
共享模块 — 跨项目复用的工具

每个项目的代码在 projects/ 下独立开发，
但有些东西所有项目都要用，放在这里：
  - llm_client.py: Qwen/OpenAI 客户端初始化
  - (未来) embedding_client.py, vector_store.py 等
"""
