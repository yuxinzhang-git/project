from urllib.parse import quote_plus
import re

from app.browser import BrowserError


class BilibiliNavigation:
    HOME_URL = "https://www.bilibili.com"
    SEARCH_URL = "https://search.bilibili.com/all?keyword={keyword}"
    CHANNEL_URL = "https://space.bilibili.com/{channel_id}"
    FAVORITES_URL = "https://space.bilibili.com/{user_id}/favlist"
    HISTORY_URL = "https://www.bilibili.com/account/history"

    def __init__(self, browser):
        self.browser = browser

    def open_home(self):    # 打开首页
        return self.browser.open(self.HOME_URL)

    def search(self, keyword):
        if not keyword.strip():
            raise BrowserError("search keyword cannot be empty")
        return self.browser.open(self.SEARCH_URL.format(keyword=quote_plus(keyword.strip())))

    def open_channel(self, channel_id): # 打开用户空间
        if not channel_id.strip():
            raise BrowserError("channel id cannot be empty")
        return self.browser.open(self.CHANNEL_URL.format(channel_id=quote_plus(channel_id.strip())))

    def open_favorites(self, user_id=None):
        user_id = (user_id or "").strip()
        if not user_id:
            # The personal favorites URL requires the logged-in user's mid.
            # Resolve it from the visible home-page account link instead of
            # reading cookies or browser storage.
            self.open_home()
            links = self.browser.links("a[href*='space.bilibili.com/']", limit=30)
            for link in links:
                match = re.search(r"space\.bilibili\.com/(\d+)", link["href"])
                if match:
                    user_id = match.group(1)
                    break
        if not user_id:
            raise BrowserError("Bilibili favorites requires a logged-in user; current user id could not be identified")
        return self.browser.open(self.FAVORITES_URL.format(user_id=quote_plus(user_id)))

    def open_history(self):
        return self.browser.open(self.HISTORY_URL)

    def back(self):
        return self.browser.back()
