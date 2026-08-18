from urllib.parse import quote_plus

from app.browser import BrowserError

from .errors import XianyuBrowserError


class XianyuNavigation:
    HOME_URL = "https://www.goofish.com/"
    SEARCH_URL = "https://www.goofish.com/search?q={keyword}"

    def __init__(self, browser):
        self.browser = browser

    def open_home(self):
        return self._open(self.HOME_URL)

    def search(self, keyword):
        if not keyword or not keyword.strip():
            raise BrowserError("search keyword cannot be empty")
        return self._open(self.SEARCH_URL.format(keyword=quote_plus(keyword.strip())))

    def back(self):
        try:
            return self.browser.back()
        except BrowserError as exc:
            raise XianyuBrowserError(str(exc)) from exc

    def _open(self, url):
        try:
            return self.browser.open(url)
        except BrowserError as exc:
            raise XianyuBrowserError(str(exc)) from exc
