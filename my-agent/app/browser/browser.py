from __future__ import annotations

from pathlib import Path
from threading import RLock
from urllib.parse import quote_plus, urljoin

from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright


class BrowserError(RuntimeError):
    """Raised when a browser operation cannot be completed."""


class Browser:
    """Project browser facade. Business code must use this class only."""

    def __init__(self, profile_dir: str | Path | None = None, headless: bool = False):
        project_root = Path(__file__).resolve().parents[2]
        self.profile_dir = Path(profile_dir or project_root / "data" / "browser" / "profile").resolve()
        self.headless = headless
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._lock = RLock()

    def _ensure_page(self) -> Page:
        if self._context is None:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            self._playwright = sync_playwright().start()    # 启动 Playwright 并返回一个 Playwright 对象，允许与浏览器进行交互。
            try:
                self._context = self._playwright.chromium.launch_persistent_context(
                    # chromium.launch_persistent_context()：
                    # 启动 Edge 系浏览器，并创建一个持久化 BrowserContext。
                    user_data_dir=str(self.profile_dir),
                    channel="msedge",
                    headless=self.headless,
                    viewport={"width": 1440, "height": 900},
                )
            except Exception as exc:
                self._reset()
                message = str(exc).lower()
                if "another instance" in message or "user data dir" in message:
                    raise BrowserError("项目专用 Edge 会话正在被占用。请关闭该 Browser 窗口后重试，或重启服务。") from exc
                raise
        if self._page is None or self._page.is_closed():
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        return self._page

    def _reset(self) -> None:
        """Discard cached browser handles even when a close operation failed."""
        context, playwright = self._context, self._playwright
        self._context = None
        self._page = None
        self._playwright = None
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                pass

    @staticmethod
    def _was_closed(error: Exception) -> bool:
        message = str(error).lower()
        if "another instance" in message or "user data dir" in message:
            return False
        return any(marker in message for marker in (
            "target page, context or browser has been closed",
            "browser has been closed",
            "context has been closed",
            "page has been closed",
        ))

    def _run(self, operation):
        with self._lock:
            try:
                return operation(self._ensure_page())
            except Exception as exc:
                if self._was_closed(exc):
                    self._reset()
                    try:
                        return operation(self._ensure_page())
                    except Exception as retry_exc:
                        raise BrowserError(str(retry_exc)) from retry_exc
                raise BrowserError(str(exc)) from exc

    def open(self, url: str) -> dict:
        """Open a URL and return its current page metadata."""
        if not url.strip():
            raise BrowserError("url cannot be empty")

        def navigate(page: Page) -> dict:
            # 导航到指定URL，等待DOM内容加载完成，超时时间为60秒
            page.goto(url.strip(), wait_until="domcontentloaded", timeout=60_000)
            return {"title": page.title(), "url": page.url}

        return self._run(navigate)

    def back(self) -> dict:
        """Go back one browser-history entry and return page metadata."""

        def navigate(page: Page) -> dict:
            page.go_back(wait_until="domcontentloaded", timeout=60_000)
            return {"title": page.title(), "url": page.url}

        return self._run(navigate)

    def search(self, keyword: str) -> dict:
        """Search Baidu by default."""
        if not keyword.strip():
            raise BrowserError("keyword cannot be empty")
        return self.open(f"https://www.baidu.com/s?wd={quote_plus(keyword.strip())}")

    def click(self, locator: str) -> dict:
        return self.click_nth(locator, 1)

    def click_nth(self, locator: str, index: int) -> dict:
        """Click a one-based item in a locator result set."""
        if not locator.strip():
            raise BrowserError("locator cannot be empty")
        if index < 1:
            raise BrowserError("index must be at least 1")

        def click_target(page: Page) -> dict:
            target = page.locator(locator)  # 根据 CSS Selector、XPath 等定位页面元素
            if target.count() < index:
                raise BrowserError(f"only found {target.count()} matching elements")
            existing_pages = set(page.context.pages)
            target.nth(index - 1).click(timeout=15_000)
            page.wait_for_timeout(500)
            opened_pages = [item for item in page.context.pages if item not in existing_pages and not item.is_closed()]
            if opened_pages:
                self._page = opened_pages[-1]
                try:
                    self._page.wait_for_load_state("domcontentloaded", timeout=15_000)
                except Exception:
                    pass
                page = self._page
            return {"title": page.title(), "url": page.url}

        return self._run(click_target)

    def type(self, locator: str, text: str) -> dict:
        if not locator.strip():
            raise BrowserError("locator cannot be empty")

        def fill_target(page: Page) -> dict:
            page.locator(locator).first.fill(text)
            return {"title": page.title(), "url": page.url}

        return self._run(fill_target)

    def press(self, locator: str, key: str) -> dict:
        """Press a keyboard key on a visible control."""
        if not locator.strip() or not key.strip():
            raise BrowserError("locator and key cannot be empty")

        def press_target(page: Page) -> dict:
            page.locator(locator).first.press(key)
            page.wait_for_timeout(300)
            return {"title": page.title(), "url": page.url}

        return self._run(press_target)

    def text(self, locator: str) -> str:
        """Read visible text without exposing the underlying Playwright page."""
        if not locator.strip():
            raise BrowserError("locator cannot be empty")
        return self._run(lambda page: page.locator(locator).first.inner_text(timeout=15_000))

    # 让agent看懂有哪些可交互的元素，方便用户选择
    def interactive_elements(self, limit: int = 30) -> list[dict]:
        """Return a compact, user-facing summary of visible page controls."""

        def collect(page: Page) -> list[dict]:
            selector = "input, textarea, button, a, [role='button']"
            controls = page.locator(selector)
            count = min(controls.count(), limit)
            results = []
            for index in range(count):
                control = controls.nth(index)
                if not control.is_visible():
                    continue
                details = control.evaluate(
                    """element => ({
                        tag: element.tagName.toLowerCase(),
                        text: (element.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 80),
                        placeholder: element.getAttribute('placeholder') || '',
                        ariaLabel: element.getAttribute('aria-label') || '',
                        name: element.getAttribute('name') || '',
                        id: element.id || '',
                        type: element.getAttribute('type') || ''
                    })"""
                )
                label = details["text"] or details["placeholder"] or details["ariaLabel"] or details["name"]
                if not label:
                    continue
                locator = None
                if details["id"]:
                    locator = f"#{details['id']}"
                elif details["name"]:
                    locator = f"{details['tag']}[name=\"{details['name']}\"]"
                elif details["placeholder"]:
                    locator = f"{details['tag']}[placeholder=\"{details['placeholder']}\"]"
                if locator:
                    results.append({"label": label, "kind": details["tag"], "type": details["type"], "locator": locator})
            return results

        return self._run(collect)

    def texts(self, locator: str, limit: int = 20) -> list[str]:
        """Return visible, non-empty text from matching elements."""
        if not locator.strip():
            raise BrowserError("locator cannot be empty")

        def collect(page: Page) -> list[str]:
            elements = page.locator(locator)
            values = []
            for index in range(min(elements.count(), limit)):
                element = elements.nth(index)
                if not element.is_visible():
                    continue
                text = element.inner_text(timeout=5_000).strip()
                if text and text not in values:
                    values.append(text[:120])
            return values

        return self._run(collect)

    def links(self, locator: str, limit: int = 100) -> list[dict]:
        """Return visible link text and resolved URLs for a locator."""
        if not locator.strip():
            raise BrowserError("locator cannot be empty")

        def collect(page: Page) -> list[dict]:
            elements = page.locator(locator)
            values = []
            for index in range(min(elements.count(), limit)):
                element = elements.nth(index)
                if not element.is_visible():
                    continue
                href = element.get_attribute("href")
                if not href:
                    continue
                text = element.inner_text(timeout=5_000).strip()
                values.append({"text": text[:120], "href": urljoin(page.url, href)})
            return values

        return self._run(collect)

    # 结构化网页列表提取
    def card_links(
        self,
        card_locator: str,
        link_locator: str,
        title_locator: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Return one visible primary link from each visible result card in DOM order."""
        if not card_locator.strip() or not link_locator.strip():
            raise BrowserError("card and link locators cannot be empty")

        def collect(page: Page) -> list[dict]:
            cards = page.locator(card_locator)
            values = []
            for index in range(cards.count()):
                card = cards.nth(index)
                if not card.is_visible():
                    continue
                # Some sites use the result anchor itself as the card. Include
                # that anchor before searching for nested links.
                if card.evaluate("(element, selector) => element.matches(selector)", link_locator):
                    links = [card]
                else:
                    nested_links = card.locator(link_locator)
                    links = [nested_links.nth(link_index) for link_index in range(nested_links.count())]
                for link in links:
                    if not link.is_visible():
                        continue
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    text = link.inner_text(timeout=5_000).strip()
                    if title_locator:
                        titles = card.locator(title_locator)
                        if titles.count() and titles.first.is_visible():
                            text = titles.first.inner_text(timeout=5_000).strip() or text
                    attributes = card.evaluate(
                        "element => Object.fromEntries(Array.from(element.attributes).map(attribute => [attribute.name, attribute.value]))"
                    )
                    values.append(
                        {
                            "text": text[:120],
                            "card_text": card.inner_text(timeout=5_000).strip()[:500],
                            "href": urljoin(page.url, href),
                            "card_class": card.get_attribute("class") or "",
                            "card_aria": card.get_attribute("aria-label") or "",
                            "card_attributes": attributes,
                        }
                    )
                    break
                if len(values) >= limit:
                    break
            return values

        return self._run(collect)

    def screenshot(self, path: str | Path) -> dict:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = Path.cwd() / target
        target.parent.mkdir(parents=True, exist_ok=True)

        def capture(page: Page) -> dict:
            page.screenshot(path=str(target), full_page=True)
            return {"path": str(target), "title": page.title(), "url": page.url}

        return self._run(capture)

    def state(self) -> dict:
        def read_state(page: Page) -> dict:
            return {"title": page.title(), "url": page.url, "profile_dir": str(self.profile_dir)}

        return self._run(read_state)

    def close(self) -> None:
        with self._lock:
            self._reset()
