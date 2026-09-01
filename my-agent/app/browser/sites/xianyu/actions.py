from .components import XianyuItemList, XianyuMarketData, XianyuPagination


class XianyuActions:
    def __init__(self, browser):
        self.browser = browser
        self.items = XianyuItemList(browser)
        self.pagination = XianyuPagination(browser)

    def list_items(self, limit=20):
        return self.items.list(limit)

    def ensure_page_ready(self):
        self.items.ensure_ready()

    def open_item(self, index):
        return self.items.open(index)

    def next_page(self):
        return self.pagination.next()

    def previous_page(self):
        return self.pagination.previous()

    def estimate_items(self, items):
        return XianyuMarketData.estimate(items)
