from ..actions import BilibiliVideoList
from ..components import BilibiliPagination


class BilibiliSearchPage:
    def __init__(self, browser):
        self.video_list = BilibiliVideoList(browser)
        self.pagination = BilibiliPagination(browser)
