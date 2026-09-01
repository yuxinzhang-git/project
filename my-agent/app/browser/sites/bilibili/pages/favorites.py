from ..components import BilibiliContentCollection


class BilibiliFavoritesPage:
    def __init__(self, browser):
        self.browser = browser
        self.collection = BilibiliContentCollection(browser)
