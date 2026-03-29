"""
QuoteBot Web UI - 带浏览器画面的对话式 Agent 界面
使用线程隔离 Agent 任务，避免阻塞事件循环
"""

import asyncio
import json
import base64
import threading
import queue
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from llm_planner import LLMPlanner
from browser_engine import BrowserEngine
from data_parser import DataParser
from config import Config
from main import execute_action, dedupe_quotes

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"


class AgentWorker:
    def __init__(self):
        self.msg_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()

    def enqueue(self, msg_type: str, data: dict):
        self.msg_queue.put({"type": msg_type, **data})

    def run(self, instruction: str):
        import asyncio as _asyncio

        self._stop_event.clear()
        self.enqueue("message", {"role": "assistant", "text": f"🎯 开始执行: {instruction}"})

        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)

        try:
            browser = BrowserEngine()
            llm = LLMPlanner()

            print("[Agent] 启动浏览器...")
            loop.run_until_complete(browser.start())
            print("[Agent] 浏览器启动完成")

            loop.run_until_complete(browser.goto(Config.TARGET_URL))
            self._send_screenshot(browser, loop, "首页加载完成")

            collected_quotes = []
            max_steps = Config.MAX_STEPS
            repeated_action_count = 0
            last_action_signature = None

            for step in range(max_steps):
                if self._stop_event.is_set():
                    self.enqueue("message", {"role": "warning", "text": "⏹️ 用户手动停止"})
                    break

                page_summary = loop.run_until_complete(browser.get_page_summary())
                self._send_screenshot(browser, loop, f"步骤 {step + 1} - 感知")

                self.enqueue("message", {
                    "role": "thinking",
                    "text": f"🧠 第 {step + 1} 步：正在思考...",
                })

                decision = llm.plan(instruction, page_summary, collected_quotes)
                thought = decision.get("thought", "")
                action = decision.get("action", "")
                params = decision.get("params", {})

                action_signature = json.dumps(
                    {"action": action, "params": params},
                    ensure_ascii=False, sort_keys=True,
                )
                if action_signature == last_action_signature:
                    repeated_action_count += 1
                else:
                    repeated_action_count = 1
                    last_action_signature = action_signature

                if repeated_action_count > 2 and action in ("EXTRACT", "SCROLL", "NAVIGATE", "CLICK"):
                    self.enqueue("message", {
                        "role": "warning",
                        "text": f"🔄 检测到重复动作 ({action} x{repeated_action_count})，停止探索",
                    })
                    break

                self.enqueue("message", {
                    "role": "thought",
                    "text": f"💭 {thought}\n🎬 动作: {action}" + (f"\n📋 参数: {json.dumps(params, ensure_ascii=False)}" if params else ""),
                })

                if action == "DONE":
                    self.enqueue("message", {"role": "success", "text": "✅ 任务完成!"})
                    break

                try:
                    new_quotes = loop.run_until_complete(execute_action(browser, action, params))
                    if action in ("CLICK", "NAVIGATE", "BACK"):
                        self._send_screenshot(browser, loop, f"{action}: {params.get('target', params.get('url', ''))}")
                    elif action == "SCROLL":
                        self._send_screenshot(browser, loop, f"滚动: {params.get('direction', 'down')}")
                    elif action == "EXTRACT":
                        self._send_screenshot(browser, loop, "提取名言")
                except Exception as e:
                    self.enqueue("message", {"role": "warning", "text": f"⚠️ 动作失败: {e}"})
                    if action in ("CLICK", "NAVIGATE", "BACK"):
                        self.enqueue("message", {"role": "info", "text": "↪️ 改为提取当前页面"})
                        new_quotes = loop.run_until_complete(execute_action(browser, "EXTRACT", {"selector": ".quote"}))
                    else:
                        loop.run_until_complete(browser.scroll("down"))
                        new_quotes = []

                if new_quotes:
                    before_count = len(collected_quotes)
                    collected_quotes = dedupe_quotes(collected_quotes + new_quotes)
                    added = len(collected_quotes) - before_count
                    label = f"📝 已提取 {len(new_quotes)} 条"
                    if params.get("author"):
                        label += f"（作者: {params['author']}）"
                    label += f"（新增有效 {added} 条）"
                    self.enqueue("message", {"role": "info", "text": label})

                    requested_count = params.get("count", 0) if action == "EXTRACT" else 0
                    if requested_count and len(collected_quotes) >= requested_count:
                        self.enqueue("message", {"role": "success", "text": f"🎯 已满足 {requested_count} 条要求，提前结束"})
                        break

                loop.run_until_complete(browser.wait_for_load())

            if not collected_quotes:
                collected_quotes = dedupe_quotes(loop.run_until_complete(browser.get_page_quotes()))

            result_text = f"📊 共找到 {len(collected_quotes)} 条名言\n\n"
            for i, q in enumerate(collected_quotes[:10], 1):
                result_text += f'{i}. "{q["text"][:80]}…" —— {q["author"]}\n'

            self.enqueue("message", {"role": "result", "text": result_text})

            DataParser.save_result({"instruction": instruction, "quotes": collected_quotes, "steps_taken": step + 1}, "output/web_result.json")
            DataParser.generate_html_report({"instruction": instruction, "quotes": collected_quotes, "steps_taken": step + 1}, "output/web_result.html")

        except Exception as e:
            self.enqueue("message", {"role": "warning", "text": f"⚠️ 错误: {e}"})
            import traceback
            traceback.print_exc()
        finally:
            try:
                loop.run_until_complete(browser.close())
            except:
                pass
            loop.close()

    def _send_screenshot(self, browser, loop, label):
        try:
            png_bytes = loop.run_until_complete(browser.page.screenshot(type="png"))
            b64 = base64.b64encode(png_bytes).decode()
            self.enqueue("screenshot", {"image": b64, "url": browser.page.url, "step": label})
        except Exception as e:
            print(f"[截图失败] {e}")

    def stop(self):
        self._stop_event.set()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    worker = AgentWorker()
    worker_thread = None

    async def forward_messages():
        while True:
            try:
                msg = await asyncio.get_event_loop().run_in_executor(None, worker.msg_queue.get, True, 0.5)
                await websocket.send_json(msg)
            except queue.Empty:
                continue
            except Exception:
                break

    forward_task = None
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            print(f"[WS] 收到: {msg_type}")

            if msg_type == "start":
                instruction = data.get("instruction", "")
                if instruction and (worker_thread is None or not worker_thread.is_alive()):
                    if forward_task is None or forward_task.done():
                        forward_task = asyncio.create_task(forward_messages())
                    worker_thread = threading.Thread(target=worker.run, args=(instruction,), daemon=True)
                    worker_thread.start()
            elif msg_type == "stop":
                worker.stop()
    except WebSocketDisconnect:
        pass
    finally:
        worker.stop()
        if forward_task:
            forward_task.cancel()


@app.get("/")
async def index():
    return HTMLResponse((STATIC_DIR / "index.html").read_text())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
