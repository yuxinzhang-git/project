from urllib.parse import quote_plus

from app.browser import BrowserError


class TaobaoNavigation:
    HOME_URL = "https://www.taobao.com"
    SEARCH_URL = "https://s.taobao.com/search?q={keyword}"

    def __init__(self, browser):
        self.browser = browser

    def open_home(self):
        return self.browser.open(self.HOME_URL)

    def search(self, keyword):
        if not keyword.strip():
            raise BrowserError("search keyword cannot be empty")
        return self.browser.open(self.SEARCH_URL.format(keyword=quote_plus(keyword.strip())))

    def open_favorites(self):
        return self.browser.open("https://i.taobao.com/my_taobao.htm?spm=a21bo.2017.201864-1.1")

    def back(self):
        return self.browser.back()
