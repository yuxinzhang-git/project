from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from app.browser import BrowserError
from app.browser.components import Pagination


class BilibiliPagination(Pagination):
    NEXT_CONTROLS = (".vui_pagenation--btn-next", "button[aria-label*='下一页']", "text=下一页")
    PREVIOUS_CONTROLS = (".vui_pagenation--btn-prev", "button[aria-label*='上一页']", "text=上一页")

    def __init__(self, browser):
        self.browser = browser

    def _click_any(self, controls, action):
        for locator in controls:
            try:
                return {**self.browser.click(locator), "action": action}
            except BrowserError:
                continue
        raise BrowserError(f"Bilibili {action} control was not found")

    def next(self):
        return self._click_any(self.NEXT_CONTROLS, "moved to next search page")

    def previous(self):
        return self._click_any(self.PREVIOUS_CONTROLS, "moved to previous search page")

    def goto(self, page):
        if page < 1:
            raise BrowserError("page must be at least 1")
        state = self.browser.state()
        parsed = urlparse(state["url"])
        if "search.bilibili.com" not in parsed.netloc:
            raise BrowserError("pagination is only available on a Bilibili search page")
        query = parse_qs(parsed.query)
        query["page"] = [str(page)]
        target = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
        result = self.browser.open(target)
        return {**result, "action": f"moved to search page {page}"}
