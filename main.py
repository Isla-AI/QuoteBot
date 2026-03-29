"""
QuoteBot - 智能名言探索代理
基于 Playwright + LLM (GLM-5) 的 Agentic Web Browser

用法：
    python main.py "找三条关于爱情的名言"
    python main.py "爱因斯坦有哪些名言？"
    python main.py "给我一个随机名言"
    python main.py --demo          # 运行演示模式
    python main.py --interactive   # 交互模式
"""

import sys
import json
import asyncio
from datetime import datetime
from llm_planner import LLMPlanner
from browser_engine import BrowserEngine
from data_parser import DataParser
from config import Config


def _quote_key(quote: dict) -> tuple:
    return (
        (quote.get("text") or "").strip(),
        (quote.get("author") or "").strip(),
    )


def dedupe_quotes(quotes: list[dict]) -> list[dict]:
    """按文本 + 作者去重，保留首次出现顺序"""
    unique_quotes = []
    seen = set()

    for quote in quotes:
        key = _quote_key(quote)
        if key in seen:
            continue
        seen.add(key)
        unique_quotes.append(quote)

    return unique_quotes


def build_output_path(prefix: str) -> tuple[str, str]:
    """为 JSON 和 HTML 生成稳定且不冲突的输出路径"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{prefix}_{timestamp}"
    return (
        f"{Config.OUTPUT_DIR}/{base_name}.json",
        f"{Config.OUTPUT_DIR}/{base_name}.html",
    )


async def execute_action(browser: BrowserEngine, action: str, params: dict) -> list[dict]:
    """执行单步动作，统一返回新增提取结果"""
    if action == "DONE":
        return []
    if action == "CLICK":
        target = params.get("target", "")
        await browser.click(target)
        print(f"👆 已点击: {target}")
        return []
    if action == "NAVIGATE":
        url = params.get("url", "")
        await browser.goto(url)
        print(f"🌐 已导航到: {url}")
        return []
    if action == "SCROLL":
        direction = params.get("direction", "down")
        await browser.scroll(direction)
        print(f"📜 已滚动: {direction}")
        return []
    if action == "EXTRACT":
        count = params.get("count", 0)
        author = params.get("author")
        quotes = await browser.get_page_quotes(author=author)
        if count and count > 0:
            quotes = quotes[:count]
        if author:
            print(f"📝 已提取 {len(quotes)} 条作者为 {author} 的名言")
        else:
            print(f"📝 已提取 {len(quotes)} 条名言")
        return quotes
    if action == "BACK":
        await browser.go_back()
        print(f"⬅️ 已返回上一页")
        return []

    raise ValueError(f"未知动作: {action}")


async def agent_loop(user_instruction: str, llm: LLMPlanner, browser: BrowserEngine) -> dict:
    """
    Agent 主循环：感知 → 思考 → 行动 → 反馈
    """
    print(f"\n🎯 用户指令: {user_instruction}")
    print("=" * 60)

    # 导航到首页
    await browser.goto(Config.TARGET_URL)

    collected_quotes = []
    max_steps = Config.MAX_STEPS
    repeated_action_count = 0
    last_action_signature = None
    steps_taken = 0

    for step in range(max_steps):
        steps_taken = step + 1
        print(f"\n--- 步骤 {step + 1}/{max_steps} ---")

        # 1. 感知：获取当前页面信息
        page_summary = await browser.get_page_summary()
        print(f"📄 页面摘要获取完成")

        # 2. 思考：让 LLM 决策下一步行动
        print(f"🧠 LLM 正在思考...")
        decision = llm.plan(user_instruction, page_summary, collected_quotes)

        thought = decision.get("thought", "")
        action = decision.get("action", "")
        params = decision.get("params", {})

        action_signature = json.dumps(
            {"action": action, "params": params},
            ensure_ascii=False,
            sort_keys=True,
        )

        # 检测重复动作：相同动作+参数连续执行超过 2 次则停止
        if action_signature == last_action_signature:
            repeated_action_count += 1
        else:
            repeated_action_count = 1
            last_action_signature = action_signature

        if repeated_action_count > 2 and action in ("EXTRACT", "SCROLL", "NAVIGATE", "CLICK"):
            print(f"🔄 检测到重复动作 ({action} x{repeated_action_count})，停止继续探索")
            break

        print(f"💭 思考: {thought}")
        print(f"🎬 动作: {action}")
        if params:
            print(f"📋 参数: {json.dumps(params, ensure_ascii=False)}")

        # 3. 行动：执行动作
        if action == "DONE":
            print(f"\n✅ 任务完成!")
            break

        try:
            new_quotes = await execute_action(browser, action, params)
        except Exception as e:
            print(f"⚠️ 动作执行失败: {e}")
            if action in ("CLICK", "NAVIGATE", "BACK"):
                print("↪️ 本步改为提取当前页面，避免空转")
                new_quotes = await execute_action(browser, "EXTRACT", {"selector": ".quote"})
            else:
                print("↪️ 本步改为向下滚动，尝试恢复上下文")
                await browser.scroll("down")
                new_quotes = []

        if new_quotes:
            before_count = len(collected_quotes)
            collected_quotes = dedupe_quotes(collected_quotes + new_quotes)
            added_count = len(collected_quotes) - before_count
            print(f"✨ 新增有效名言 {added_count} 条")

            requested_count = params.get("count", 0) if action == "EXTRACT" else 0
            if requested_count and len(collected_quotes) >= requested_count:
                print("🎯 已满足用户要求的数量，提前结束")
                break

        # 4. 等待页面加载
        await browser.wait_for_load()
    else:
        print(f"\n⏰ 达到最大步数限制 ({max_steps})")

    # 返回最终结果
    if not collected_quotes:
        collected_quotes = dedupe_quotes(await browser.get_page_quotes())

    result = {
        "instruction": user_instruction,
        "quotes": collected_quotes,
        "steps_taken": steps_taken,
    }

    return result


async def demo_mode():
    """演示模式：运行预设任务"""
    print("=" * 60)
    print("🎭 QuoteBot 演示模式")
    print("=" * 60)

    llm = LLMPlanner()

    demo_tasks = [
        "找三条关于爱情的名言",
        "爱因斯坦有哪些名言？",
        "给我一个随机名言",
    ]

    for i, task in enumerate(demo_tasks, 1):
        print(f"\n{'=' * 60}")
        print(f"📋 演示任务 {i}/{len(demo_tasks)}: {task}")
        print(f"{'=' * 60}")

        browser = BrowserEngine()
        await browser.start()
        try:
            result = await agent_loop(task, llm, browser)
            DataParser.display_result(result)
            json_path, html_path = build_output_path(f"demo_{i}")
            DataParser.save_result(result, json_path)
            DataParser.generate_html_report(result, html_path)
        finally:
            await browser.close()

        # 任务间隔
        if i < len(demo_tasks):
            print(f"\n⏳ 等待 3 秒后继续下一个任务...")
            await asyncio.sleep(3)


async def interactive_mode():
    """交互模式：用户输入指令"""
    print("=" * 60)
    print("💬 QuoteBot 交互模式")
    print("输入你的指令，输入 'quit' 退出")
    print("=" * 60)

    llm = LLMPlanner()

    browser = BrowserEngine()
    await browser.start()
    try:
        while True:
            print()
            instruction = input("🗣️ 你的指令: ").strip()

            if not instruction:
                continue
            if instruction.lower() in ("quit", "exit", "q"):
                print("👋 再见!")
                break

            result = await agent_loop(instruction, llm, browser)
            DataParser.display_result(result)
            json_path, html_path = build_output_path("interactive")
            DataParser.save_result(result, json_path)
            DataParser.generate_html_report(result, html_path)
    finally:
        await browser.close()


async def main():
    """主入口"""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--demo":
        await demo_mode()
    elif arg == "--interactive":
        await interactive_mode()
    else:
        instruction = " ".join(sys.argv[1:])
        llm = LLMPlanner()
        browser = BrowserEngine()
        await browser.start()
        try:
            result = await agent_loop(instruction, llm, browser)
            DataParser.display_result(result)
            json_path, html_path = build_output_path("result")
            DataParser.save_result(result, json_path)
            DataParser.generate_html_report(result, html_path)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
