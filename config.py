"""
QuoteBot 配置文件
"""

import os


class Config:
    # 目标网站
    TARGET_URL = "https://quotes.toscrape.com/"

    # LLM 配置（百炼 API + GLM-5）
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "glm-5")
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

    # Agent 配置
    MAX_STEPS = int(os.getenv("MAX_STEPS", "10"))
    HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

    # 输出配置
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
