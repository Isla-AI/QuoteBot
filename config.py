"""
QuoteBot 配置文件
"""

class Config:
    # 目标网站
    TARGET_URL = "https://quotes.toscrape.com/"

    # LLM 配置（百炼 API + GLM-5）
    LLM_API_KEY = "sk-sp-e18e0f06fa3c428b90be9e639400fe8e"
    LLM_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
    LLM_MODEL = "glm-5"
    LLM_MAX_TOKENS = 2000
    LLM_TEMPERATURE = 0.3

    # Agent 配置
    MAX_STEPS = 10
    HEADLESS = True  # 浏览器是否无头模式

    # 输出配置
    OUTPUT_DIR = "output"
