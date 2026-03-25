"""
浏览器引擎 - 基于 Playwright 的网页交互层（异步版本）
"""

import json
from playwright.async_api import async_playwright
from config import Config
from bs4 import BeautifulSoup


class BrowserEngine:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self):
        """启动浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=Config.HEADLESS,
        )
        self.page = await self.browser.new_page()
        return self

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def goto(self, url: str):
        """导航到指定 URL"""
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(1000)

    async def go_back(self):
        """返回上一页"""
        await self.page.go_back(wait_until="domcontentloaded")
        await self.page.wait_for_timeout(1000)

    async def click(self, target: str):
        """点击页面元素"""
        target_lower = target.lower().strip()
        # 去除可能的特殊字符
        target_clean = target_lower.replace("→", "").replace("←", "").replace(" ", "")

        if target_clean in ("next", "下一页"):
            link = self.page.locator("li.next a")
        elif target_clean in ("previous", "上一页"):
            link = self.page.locator("li.previous a")
        elif target_clean in ("login", "登录"):
            link = self.page.get_by_role("link", name="Login")
        elif target_clean in ("about",):
            link = self.page.locator("a[href*='/author/']").first
        else:
            # 尝试匹配标签名或作者链接
            link = self.page.locator(f"a:text-is('{target}')").first
            if await link.count() == 0:
                link = self.page.locator(f"a:has-text('{target}')").first

        await link.click()
        await self.page.wait_for_timeout(1000)

    async def scroll(self, direction: str = "down"):
        """滚动页面"""
        if direction == "down":
            await self.page.evaluate("window.scrollBy(0, 500)")
        else:
            await self.page.evaluate("window.scrollBy(0, -500)")
        await self.page.wait_for_timeout(500)

    async def wait_for_load(self):
        """等待页面加载"""
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_timeout(500)

    async def get_page_summary(self) -> str:
        """获取当前页面的结构化摘要，用于 LLM 分析"""
        url = self.page.url
        title = await self.page.title()
        html = await self.page.content()
        soup = BeautifulSoup(html, "lxml")

        # 提取名言
        quotes = []
        for q in soup.select("div.quote"):
            text_el = q.select_one(".text")
            author_el = q.select_one(".author")
            tag_els = q.select("a.tag")
            if text_el:
                quotes.append({
                    "text": text_el.get_text(strip=True).strip('""'),
                    "author": author_el.get_text(strip=True) if author_el else "未知",
                    "tags": [t.get_text(strip=True) for t in tag_els],
                })

        # 提取导航链接
        nav_links = []
        for link in soup.select("nav a, li.next a, li.previous a"):
            nav_links.append({
                "text": link.get_text(strip=True),
                "href": link.get("href", ""),
            })

        # 提取标签
        tags = []
        for tag in soup.select("a.tag"):
            tags.append(tag.get_text(strip=True))

        summary = {
            "url": url,
            "title": title,
            "quotes_count": len(quotes),
            "quotes": quotes,
            "navigation": nav_links,
            "top_tags": list(set(tags))[:10],
        }

        return json.dumps(summary, ensure_ascii=False, indent=2)

    async def get_page_quotes(self) -> list:
        """提取当前页面的所有名言"""
        html = await self.page.content()
        soup = BeautifulSoup(html, "lxml")

        quotes = []
        for q in soup.select("div.quote"):
            text_el = q.select_one(".text")
            author_el = q.select_one(".author")
            tag_els = q.select("a.tag")
            if text_el:
                quotes.append({
                    "text": text_el.get_text(strip=True).strip('""'),
                    "author": author_el.get_text(strip=True) if author_el else "未知",
                    "tags": [t.get_text(strip=True) for t in tag_els],
                })

        return quotes
