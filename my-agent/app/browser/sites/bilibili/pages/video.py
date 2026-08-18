from ..actions import BilibiliPlayer


class BilibiliVideoPage:
    def __init__(self, browser):
        self.player = BilibiliPlayer(browser)
