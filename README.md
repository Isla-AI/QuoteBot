# 🎡 QuoteBot - 智能名言探索代理

基于 **Playwright + LLM (GLM-5)** 的智能网页浏览代理，自动探索 [quotes.toscrape.com](https://quotes.toscrape.com/) 并收集名言。

## 项目简介

QuoteBot 展示了 AI Agent 的核心能力：

- **感知 (Perception)** — 通过 Playwright 获取网页内容
- **思考 (Thinking)** — 通过 GLM-5 分析页面并决策下一步行动
- **行动 (Action)** — 自动执行点击、翻页、提取等操作
- **Web UI** — 带浏览器画面的实时交互界面

### 演示效果

用户可以用自然语言下达指令，例如：

| 指令 | 行为 |
|------|------|
| "找三条关于爱情的名言" | 点击 love 标签 → 提取 3 条 → 早停完成 |
| "爱因斯坦有哪些名言？" | 用 author 过滤 → 直接提取爱因斯坦的名言 |
| "给我一个随机名言" | 提取当前页面 1 条名言 |
| "找五条关于励志的名言" | 点击 inspirational 标签 → 提取 5 条 |

## 技术架构

```
用户指令
   ↓
┌──────────────┐
│   LLM 层     │  ← GLM-5 (百炼 API)：接收用户意图 + 页面信息，输出行动决策
└──────┬───────┘
       ↓ JSON 指令（含 action 校验 + 参数清洗）
┌──────────────┐
│ Playwright层  │  ← 执行：点击、翻页、输入、滚动、截图
└──────┬───────┘
       ↓ 返回页面 DOM
┌──────────────┐
│  数据提取层   │  ← BeautifulSoup 解析名言、作者、标签（支持 author 过滤）
└──────┬───────┘
       ↓ 去重 + 早停
┌──────────────┐
│  输出/展示层  │  ← JSON 结果 + HTML 报告 + WebSocket 实时推送
└──────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量

```bash
export LLM_API_KEY="your-api-key"
export LLM_MODEL="glm-5"                        # 可选，默认 glm-5
export LLM_BASE_URL="https://coding.dashscope.aliyuncs.com/v1"  # 可选
```

### 3. 运行

```bash
# 单条指令模式
python main.py "找三条关于爱情的名言"

# 演示模式（自动运行 3 个预设任务）
python main.py --demo

# 交互模式（持续对话）
python main.py --interactive

# Web UI 模式（推荐）
python web_app.py
# 然后打开浏览器访问 http://localhost:8765
```

### 4. 查看结果

结果保存在 `output/` 目录：
- `*.json` — 结构化数据
- `*.html` — 可视化报告（可在浏览器中打开）

## Web UI

Web 界面提供实时交互体验：

- **左侧**：对话面板，显示 Agent 的思考过程、动作和结果
- **右侧**：实时浏览器截图，每一步操作后自动更新
- **快捷按钮**：随机名言、爱情名言、爱因斯坦、励志名言等
- **支持停止**：可随时中断正在执行的任务

```
启动：python web_app.py
访问：http://localhost:8765
```

## 项目结构

```
quote-bot/
├── main.py              # 入口 + Agent 循环 + 去重/早停/错误恢复
├── web_app.py           # Web UI 服务（FastAPI + WebSocket）
├── config.py            # 配置文件（环境变量）
├── llm_planner.py       # LLM 规划层 + 动作校验
├── browser_engine.py    # Playwright 浏览器引擎
├── data_parser.py       # 数据解析 + JSON/HTML 输出
├── requirements.txt     # Python 依赖
├── static/
│   └── index.html       # Web UI 前端页面
└── output/              # 结果输出目录
```

## Agent 能力

### 支持的动作

| 动作 | 说明 | 参数 |
|------|------|------|
| CLICK | 点击页面上的链接或按钮 | `target`: 链接文本 |
| EXTRACT | 提取名言 | `selector`, `count`(数量), `author`(作者过滤) |
| NAVIGATE | 跳转到指定 URL | `url` |
| SCROLL | 滚动页面 | `direction`: up/down |
| BACK | 返回上一页 | 无 |
| DONE | 完成任务 | 无 |

### 智能特性

- **标签优先**：按主题查找时，优先点击对应标签而非逐页翻找
- **数量控制**：用户指定数量时，精准提取并早停
- **作者过滤**：指定作者时直接过滤，无需进入详情页
- **去重**：自动去除重复名言
- **重复检测**：动作签名级检测，连续重复 3 次自动停止
- **错误恢复**：动作执行失败时自动降级为提取当前页面
- **动作校验**：LLM 输出自动校验和清洗，确保动作合法

## 核心代码说明

### Agent 循环 (`main.py`)

```
感知 → 思考 → 行动 → 去重/早停检查 → 反馈 → 感知 → ...
```

每个循环：
1. 获取当前页面信息（截图 + 结构化摘要）
2. LLM 分析并决定下一步（输出经 _normalize_decision 校验）
3. 执行动作（含错误恢复）
4. 去重 + 检查是否满足数量要求
5. 进入下一轮

### LLM 决策 (`llm_planner.py`)

LLM 接收页面摘要，输出 JSON 格式的决策：
```json
{
  "thought": "用户想要爱情相关的名言，当前页面有 love 标签，直接点击",
  "action": "CLICK",
  "params": {"target": "love"}
}
```

所有输出经 `_normalize_decision()` 校验：
- 动作名称合法化
- 参数类型清洗
- 空参数降级处理

## 技术栈

| 组件 | 技术 |
|------|------|
| 浏览器自动化 | Playwright |
| LLM | GLM-5 (百炼 API) |
| 页面解析 | BeautifulSoup4 + lxml |
| Web 框架 | FastAPI + WebSocket |
| 语言 | Python 3.10+ |

## License

MIT
