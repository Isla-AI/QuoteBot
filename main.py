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
from llm_planner import LLMPlanner
from browser_engine import BrowserEngine
from data_parser import DataParser
from config import Config


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

    for step in range(max_steps):
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

        print(f"💭 思考: {thought}")
        print(f"🎬 动作: {action}")
        if params:
            print(f"📋 参数: {json.dumps(params, ensure_ascii=False)}")

        # 3. 行动：执行动作
        if action == "DONE":
            print(f"\n✅ 任务完成!")
            break
        elif action == "CLICK":
            target = params.get("target", "")
            await browser.click(target)
            print(f"👆 已点击: {target}")
        elif action == "NAVIGATE":
            url = params.get("url", "")
            await browser.goto(url)
            print(f"🌐 已导航到: {url}")
        elif action == "SCROLL":
            direction = params.get("direction", "down")
            await browser.scroll(direction)
            print(f"📜 已滚动: {direction}")
        elif action == "EXTRACT":
            selector = params.get("selector", ".quote")
            quotes = await browser.get_page_quotes()
            collected_quotes.extend(quotes)
            print(f"📝 已提取 {len(quotes)} 条名言")
        elif action == "BACK":
            await browser.go_back()
            print(f"⬅️ 已返回上一页")
        else:
            print(f"⚠️ 未知动作: {action}，尝试继续...")
            await browser.scroll("down")

        # 4. 等待页面加载
        await browser.wait_for_load()
    else:
        print(f"\n⏰ 达到最大步数限制 ({max_steps})")

    # 返回最终结果
    result = {
        "instruction": user_instruction,
        "quotes": collected_quotes if collected_quotes else await browser.get_page_quotes(),
        "steps_taken": min(step + 1, max_steps),
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
            DataParser.save_result(result, f"output/demo_{i}.json")
            DataParser.generate_html_report(result, f"output/demo_{i}.html")
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
            DataParser.save_result(result, f"output/interactive_{len(instruction)}.json")
            DataParser.generate_html_report(result, f"output/interactive_{len(instruction)}.html")
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
            DataParser.save_result(result, "output/result.json")
            DataParser.generate_html_report(result, "output/result.html")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
