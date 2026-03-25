"""
浏览器引擎 - 基于 Playwright 的网页交互层
"""

import json
from playwright.sync_api import sync_playwright, Page, Browser
from config import Config
from bs4 import BeautifulSoup


class BrowserEngine:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    def start(self):
        """启动浏览器"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=Config.HEADLESS,
        )
        self.page = self.browser.new_page()
        return self

    def close(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.close()

    def goto(self, url: str):
        """导航到指定 URL"""
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1000)  # 等待页面渲染

    def go_back(self):
        """返回上一页"""
        self.page.go_back(wait_until="domcontentloaded")
        self.page.wait_for_timeout(1000)

    def click(self, target: str):
        """点击页面元素"""
        target_lower = target.lower().strip()

        # 尝试按文本匹配链接
        if target_lower == "next":
            link = self.page.locator("li.next a")
        elif target_lower == "previous":
            link = self.page.locator("li.previous a")
        elif target_lower == "login":
            link = self.page.get_by_role("link", name="Login")
        elif target_lower == "about":
            link = self.page.locator("a[href*='/author/']").first
        else:
            # 尝试匹配标签名或作者链接
            link = self.page.locator(f"a:text-is('{target}')").first
            if link.count() == 0:
                link = self.page.locator(f"a:has-text('{target}')").first

        link.click()
        self.page.wait_for_timeout(1000)

    def scroll(self, direction: str = "down"):
        """滚动页面"""
        if direction == "down":
            self.page.evaluate("window.scrollBy(0, 500)")
        else:
            self.page.evaluate("window.scrollBy(0, -500)")
        self.page.wait_for_timeout(500)

    def wait_for_load(self):
        """等待页面加载"""
        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(500)

    def get_page_summary(self) -> str:
        """
        获取当前页面的结构化摘要，用于 LLM 分析
        """
        url = self.page.url
        title = self.page.title()

        # 获取页面 HTML 并解析
        html = self.page.content()
        soup = BeautifulSoup(html, "lxml")

        # 提取当前页面的名言
        quotes = []
        quote_divs = soup.select("div.quote")
        for q in quote_divs:
            text_el = q.select_one(".text")
            author_el = q.select_one(".author")
            tag_els = q.select("a.tag")

            if text_el:
                quote = {
                    "text": text_el.get_text(strip=True).strip('""'),
                    "author": author_el.get_text(strip=True) if author_el else "未知",
                    "tags": [t.get_text(strip=True) for t in tag_els],
                }
                quotes.append(quote)

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

        # 构建摘要
        summary = {
            "url": url,
            "title": title,
            "quotes_count": len(quotes),
            "quotes": quotes,
            "navigation": nav_links,
            "top_tags": list(set(tags))[:10],
        }

        return json.dumps(summary, ensure_ascii=False, indent=2)

    def get_page_quotes(self) -> list:
        """提取当前页面的所有名言"""
        html = self.page.content()
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
