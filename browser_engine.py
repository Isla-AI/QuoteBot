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
        await self.page.wait_for_timeout(2000)

    async def go_back(self):
        """返回上一页"""
        await self.page.go_back(wait_until="domcontentloaded")
        await self.page.wait_for_timeout(2000)

    async def click(self, target: str):
        """点击页面元素"""
        link = await self._resolve_click_target(target)
        if await link.count() == 0:
            raise ValueError(f"页面上未找到可点击目标: {target}")

        await link.first.click()
        await self.page.wait_for_timeout(1000)

    async def _resolve_click_target(self, target: str):
        """根据目标文本解析最可能的链接"""
        target_lower = target.lower().strip()
        target_clean = target_lower.replace("→", "").replace("←", "").replace(" ", "")

        if target_clean in ("next", "下一页"):
            return self.page.locator("li.next a")
        if target_clean in ("previous", "上一页"):
            return self.page.locator("li.previous a")
        if target_clean in ("login", "登录"):
            return self.page.get_by_role("link", name="Login")
        if target_clean in ("about",):
            return self.page.locator("a[href*='/author/']")

        # 先尝试直接匹配链接文本
        link = self.page.locator(f"a:text-is('{target}')")
        if await link.count() > 0:
            return link

        link = self.page.locator(f"a:has-text('{target}')")
        if await link.count() > 0:
            return link

        # 尝试在 href 中匹配（作者名格式：Albert-Einstein）
        href_target = target.replace(" ", "-")
        link = self.page.locator(f"a[href*='/author/{href_target}']")
        if await link.count() > 0:
            return link

        # 尝试匹配标签名
        return self.page.locator(f"a.tag:has-text('{target}')")

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
        is_author_page = bool(soup.select_one("h3.author-title"))

        # 提取名言
        quotes = []
        for q in soup.select("div.quote"):
            text_el = q.select_one(".text")
            author_el = q.select_one(".author")
            tag_els = q.select("a.tag")
            if text_el:
                quotes.append({
                    "text": text_el.get_text(strip=True).strip('\u201c\u201d'),
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
            "page_type": "author" if is_author_page else "quotes",
            "quotes_count": len(quotes),
            "quotes": quotes,
            "navigation": nav_links,
            "top_tags": list(dict.fromkeys(tags))[:10],
        }

        return json.dumps(summary, ensure_ascii=False, indent=2)

    async def get_page_quotes(self, author: str | None = None) -> list:
        """提取当前页面的所有名言（支持普通页和作者详情页）"""
        html = await self.page.content()
        soup = BeautifulSoup(html, "lxml")

        quotes = []
        author_filter = (author or "").strip().lower()

        # 检查是否是作者详情页
        author_tag = soup.select_one("h3.author-title")
        if author_tag:
            author_name = author_tag.get_text(strip=True)
            born_date = soup.select_one(".author-born-date")
            born_location = soup.select_one(".author-born-location")
            description = soup.select_one(".author-description")
            born_info = ""
            if born_date:
                born_info += born_date.get_text(strip=True)
            if born_location:
                born_info += " " + born_location.get_text(strip=True)
            quotes.append({
                "text": description.get_text(strip=True)[:500] if description else "无描述",
                "author": author_name,
                "tags": ["Born: " + born_info.strip()] if born_info else [],
            })
            if author_filter and author_name.lower() != author_filter:
                return []
            return quotes

        # 普通页面：提取名言
        for q in soup.select("div.quote"):
            text_el = q.select_one(".text")
            author_el = q.select_one(".author")
            tag_els = q.select("a.tag")
            if text_el:
                author_name = author_el.get_text(strip=True) if author_el else "未知"
                if author_filter and author_name.lower() != author_filter:
                    continue
                quotes.append({
                    "text": text_el.get_text(strip=True).strip('\u201c\u201d'),
                    "author": author_name,
                    "tags": [t.get_text(strip=True) for t in tag_els],
                })

        return quotes
