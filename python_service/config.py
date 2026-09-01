"""
配置管理 — 从项目根目录 .env 读取
"""

import os
from dotenv import load_dotenv

# 加载项目根目录的 .env（和 Laravel 共用）
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


class Settings:
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen3.7-plus")
    QWEN_BASE_URL: str = os.getenv(
        "QWEN_BASE_URL",
        "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    )


settings = Settings()
