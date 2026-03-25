# 🎡 QuoteBot - 智能名言探索代理

基于 **Playwright + LLM (GLM-5)** 的智能网页浏览代理，自动探索 [quotes.toscrape.com](https://quotes.toscrape.com/) 并收集名言。

## 项目简介

QuoteBot 展示了 AI Agent 的核心能力：

- **感知 (Perception)** — 通过 Playwright 获取网页内容
- **思考 (Thinking)** — 通过 GLM-5 分析页面并决策下一步行动
- **行动 (Action)** — 自动执行点击、翻页、提取等操作

### 演示效果

用户可以用自然语言下达指令，例如：

| 指令 | 行为 |
|------|------|
| "找三条关于爱情的名言" | 遍历页面 → 筛选含"love"标签的名言 → 返回结果 |
| "爱因斯坦有哪些名言？" | 点击作者链接 → 导航到作者页 → 提取所有名言 |
| "给我一个随机名言" | 随机选择一条名言返回 |

## 技术架构

```
用户指令
   ↓
┌──────────────┐
│   LLM 层     │  ← GLM-5 (百炼 API)：接收用户意图 + 页面信息，输出行动决策
└──────┬───────┘
       ↓ JSON 指令
┌──────────────┐
│ Playwright层  │  ← 执行：点击、翻页、输入、滚动
└──────┬───────┘
       ↓ 返回页面 DOM
┌──────────────┐
│  数据提取层   │  ← BeautifulSoup 解析名言、作者、标签
└──────┬───────┘
       ↓
┌──────────────┐
│  输出/展示层  │  ← JSON 结果 + HTML 可视化报告
└──────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 运行

```bash
# 单条指令模式
python main.py "找三条关于爱情的名言"

# 演示模式（自动运行 3 个预设任务）
python main.py --demo

# 交互模式（持续对话）
python main.py --interactive
```

### 3. 查看结果

结果保存在 `output/` 目录：
- `*.json` — 结构化数据
- `*.html` — 可视化报告（可在浏览器中打开）

## 项目结构

```
quote-bot/
├── main.py              # 入口：接收用户指令，启动 Agent 循环
├── config.py            # 配置文件（API Key、模型、参数）
├── llm_planner.py       # LLM 规划层：调用 GLM-5 进行决策
├── browser_engine.py    # Playwright 浏览器引擎
├── data_parser.py       # 数据解析 + JSON/HTML 输出
├── requirements.txt     # Python 依赖
└── output/              # 结果输出目录
    ├── result.json
    └── result.html
```

## 核心代码说明

### Agent 循环 (`main.py`)

```
感知 → 思考 → 行动 → 反馈 → 感知 → ...
```

每个循环：
1. 获取当前页面信息
2. LLM 分析并决定下一步
3. 执行动作（点击/翻页/提取）
4. 返回结果给 LLM，进入下一轮

### LLM 决策 (`llm_planner.py`)

LLM 接收页面摘要，输出 JSON 格式的决策：
```json
{
  "thought": "用户想要爱情相关的名言，当前页面没有，需要点击 love 标签",
  "action": "CLICK",
  "params": {"target": "love"}
}
```

### 浏览器引擎 (`browser_engine.py`)

封装 Playwright 操作：
- `goto()` — 导航到 URL
- `click()` — 智能点击（自动匹配文本/链接）
- `scroll()` — 滚动页面
- `get_page_summary()` — 生成页面结构化摘要供 LLM 分析

## 技术栈

| 组件 | 技术 |
|------|------|
| 浏览器自动化 | Playwright |
| LLM | GLM-5 (百炼 API) |
| 页面解析 | BeautifulSoup4 + lxml |
| 语言 | Python 3.10+ |

## License

MIT
