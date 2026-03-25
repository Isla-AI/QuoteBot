"""
数据解析与展示层
"""

import json
import os
from datetime import datetime


class DataParser:
    @staticmethod
    def display_result(result: dict):
        """在终端展示抓取结果"""
        quotes = result.get("quotes", [])
        instruction = result.get("instruction", "")
        steps = result.get("steps_taken", 0)

        print(f"\n{'=' * 60}")
        print(f"📊 执行结果")
        print(f"{'=' * 60}")
        print(f"🎯 指令: {instruction}")
        print(f"👣 步数: {steps}")
        print(f"📝 共找到 {len(quotes)} 条名言")
        print(f"{'=' * 60}")

        for i, q in enumerate(quotes, 1):
            print(f"\n  ┌─ 💬 名言 #{i}")
            print(f"  │ \"{q.get('text', '')}\"")
            print(f"  │")
            print(f"  │ —— {q.get('author', '未知')}")
            if q.get("tags"):
                print(f"  │ 🏷️  标签: {', '.join(q['tags'])}")
            print(f"  └{'─' * 50}")

        print()

    @staticmethod
    def save_result(result: dict, filepath: str):
        """保存结果到 JSON 文件"""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        output = {
            "timestamp": datetime.now().isoformat(),
            "instruction": result.get("instruction", ""),
            "steps_taken": result.get("steps_taken", 0),
            "quotes_count": len(result.get("quotes", [])),
            "quotes": result.get("quotes", []),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"💾 结果已保存到: {filepath}")

    @staticmethod
    def generate_html_report(result: dict, filepath: str):
        """生成 HTML 可视化报告"""
        quotes = result.get("quotes", [])
        instruction = result.get("instruction", "")
        steps = result.get("steps_taken", 0)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 统计信息
        all_tags = []
        all_authors = []
        for q in quotes:
            all_tags.extend(q.get("tags", []))
            all_authors.append(q.get("author", "未知"))

        # 生成 HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuoteBot - 智能名言探索代理</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 2rem;
        }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
        .header p {{ opacity: 0.8; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            color: white;
        }}
        .stat-number {{ font-size: 2rem; font-weight: bold; }}
        .stat-label {{ opacity: 0.8; font-size: 0.9rem; }}
        .quote-card {{
            background: white;
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
            position: relative;
            overflow: hidden;
        }}
        .quote-card::before {{
            content: '"';
            position: absolute;
            top: -10px;
            left: 20px;
            font-size: 8rem;
            color: #667eea;
            opacity: 0.1;
            font-family: Georgia, serif;
        }}
        .quote-text {{
            font-size: 1.2rem;
            line-height: 1.8;
            color: #333;
            margin-bottom: 1rem;
            position: relative;
            z-index: 1;
        }}
        .quote-author {{
            font-weight: bold;
            color: #667eea;
            margin-bottom: 0.5rem;
        }}
        .tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .tag {{
            background: #f0f0f0;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            color: #666;
        }}
        .footer {{
            text-align: center;
            color: rgba(255,255,255,0.6);
            margin-top: 2rem;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎡 QuoteBot</h1>
            <p>智能名言探索代理 · Playwright + LLM (GLM-5)</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{len(quotes)}</div>
                <div class="stat-label">名言数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{steps}</div>
                <div class="stat-label">执行步数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(set(all_authors))}</div>
                <div class="stat-label">作者数量</div>
            </div>
        </div>

        <div style="background: rgba(255,255,255,0.1); border-radius: 12px; padding: 1rem 1.5rem; margin-bottom: 2rem; color: white;">
            <strong>🎯 用户指令：</strong>{instruction}
        </div>
"""

        for i, q in enumerate(quotes, 1):
            tags_html = "".join(f'<span class="tag">{t}</span>' for t in q.get("tags", []))
            html += f"""
        <div class="quote-card">
            <div class="quote-text">{q.get('text', '')}</div>
            <div class="quote-author">—— {q.get('author', '未知')}</div>
            <div class="tags">{tags_html}</div>
        </div>
"""

        html += f"""
        <div class="footer">
            <p>由 QuoteBot 生成 · {timestamp}</p>
            <p>技术栈：Playwright + GLM-5 (百炼 API)</p>
        </div>
    </div>
</body>
</html>"""

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"📊 HTML 报告已生成: {filepath}")
