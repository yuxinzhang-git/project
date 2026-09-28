from ..errors import XianyuPageStructureError
from ..pages.search import XianyuSearchPage


class XianyuPagination:
    def __init__(self, browser):
        self.browser = browser

    def _click(self, selectors, label):
        for selector in selectors:
            try:
                result = self.browser.click(selector)
                return {**result, "action": label}
            except Exception:
                continue
        raise XianyuPageStructureError(f"Xianyu {label} control was not found")

    def next(self):
        return self._click(XianyuSearchPage.NEXT_BUTTONS, "opened next page")

    def previous(self):
        return self._click(XianyuSearchPage.PREVIOUS_BUTTONS, "opened previous page")
