"""
LLM 规划层 - 调用百炼 API (GLM-5) 进行决策
"""

import json
from openai import OpenAI
from config import Config

SYSTEM_PROMPT = """你是一个智能网页浏览代理（Web Agent）。你的任务是根据用户指令，自动浏览 https://quotes.toscrape.com/ 网站，找到用户需要的名言信息。

## 你的能力

你可以通过以下动作与网页交互：

| 动作 | 说明 | 参数 |
|------|------|------|
| CLICK | 点击页面上的链接或按钮 | target: 链接文本（如 "Next", "about", 标签名） |
| EXTRACT | 从当前页面提取名言 | selector: CSS 选择器（默认 ".quote"） |
| NAVIGATE | 跳转到指定 URL | url: 目标地址 |
| SCROLL | 滚动页面 | direction: "up" 或 "down" |
| BACK | 返回上一页 | 无参数 |
| DONE | 完成任务 | 无参数 |

## 输出格式

你必须严格以 JSON 格式输出，不要输出任何其他内容。格式如下：

```json
{
  "thought": "你的思考过程：分析当前页面，判断是否找到了用户需要的信息",
  "action": "动作名称",
  "params": {"参数名": "参数值"}
}
```

## 决策规则

1. 首先分析当前页面是否已有用户需要的信息
2. 如果已有，使用 EXTRACT 提取，然后输出 DONE
3. 如果没有，根据需要选择 CLICK（翻页/点标签/点作者）继续探索
4. 每次只执行一个动作，逐步完成任务
5. 最多探索 10 步，如果找不到就用 EXTRACT 提取当前页面的所有名言后输出 DONE
6. 如果用户要求"随机"，可以在任意页面提取后输出 DONE
7. 不要重复之前已经做过的动作

## 页面结构说明

- 首页显示 10 条名言，每条有引用内容、作者和标签
- 点击 "Next" 可翻到下一页
- 点击 "(about)" 可查看作者详情（出生日期、地点、描述）
- 点击标签名可查看该标签下的所有名言
- 右侧有 "Top Ten tags" 热门标签
- 总共约 10 页，100 条名言"""


class LLMPlanner:
    def __init__(self):
        self.client = OpenAI(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
        )

    def plan(self, user_instruction: str, page_summary: str, collected_quotes: list = None) -> dict:
        """
        让 LLM 分析当前状态，决定下一步行动
        """
        # 构建用户消息
        user_message = f"""## 用户指令
{user_instruction}

## 当前页面信息
{page_summary}"""

        if collected_quotes:
            user_message += f"\n\n## 已收集的名言\n"
            for i, q in enumerate(collected_quotes[-5:], 1):  # 只显示最近 5 条
                user_message += f"{i}. \"{q.get('text', '')}\" — {q.get('author', '')}\n"

        user_message += "\n\n请分析当前页面，决定下一步行动。以 JSON 格式输出。"

        try:
            response = self.client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=Config.LLM_MAX_TOKENS,
                temperature=Config.LLM_TEMPERATURE,
            )

            content = response.choices[0].message.content.strip()
            return self._parse_response(content)

        except Exception as e:
            print(f"⚠️ LLM 调用失败: {e}")
            # 降级策略：默认提取当前页面
            return {
                "thought": f"LLM 调用失败，降级为提取当前页面所有名言",
                "action": "EXTRACT",
                "params": {"selector": ".quote"},
            }

    def _parse_response(self, content: str) -> dict:
        """解析 LLM 返回的 JSON"""
        # 尝试提取 JSON 内容
        content = content.strip()

        # 处理 markdown 代码块
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        try:
            decision = json.loads(content)
            # 验证必要字段
            if "action" not in decision:
                raise ValueError("缺少 'action' 字段")
            return decision
        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON
            try:
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    decision = json.loads(content[start:end])
                    return decision
            except:
                pass

            print(f"⚠️ 无法解析 LLM 响应: {content[:200]}...")
            return {
                "thought": "LLM 响应格式异常，降级为提取当前页面",
                "action": "EXTRACT",
                "params": {"selector": ".quote"},
            }
