from ..components import BilibiliContentCollection


class BilibiliHistoryPage:
    def __init__(self, browser):
        self.browser = browser
        self.collection = BilibiliContentCollection(browser)
