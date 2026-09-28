from .components.product_list import TaobaoProductList
from .errors import TaobaoLoginRequiredError, TaobaoRiskControlError
from .navigation import TaobaoNavigation


class TaobaoAdapter:
    def __init__(self, browser):
        self.browser = browser
        self.navigation = TaobaoNavigation(browser)
        self.products = TaobaoProductList(browser)

    def capability(self):
        from .capability import capability
        return capability()

    def _guard_page(self):
        state = self.browser.state()
        marker = f"{state.get('title', '')} {state.get('url', '')}".lower()
        if any(word in marker for word in ("captcha", "verify", "security", "滑块", "验证码", "安全验证", "风险")):
            raise TaobaoRiskControlError("Taobao risk control or verification is blocking this operation; no bypass was attempted")
        if any(word in marker for word in ("login", "sign in", "登录", "请登录")):
            raise TaobaoLoginRequiredError("Taobao login is required for this operation")

    def open_home(self):
        return self.navigation.open_home()

    def search(self, keyword):
        return self.navigation.search(keyword)

    def open_favorites(self):
        result = self.navigation.open_favorites()
        self._guard_page()
        return result

    def back(self):
        return self.navigation.back()

    def list_products(self, limit=20):
        self._guard_page()
        return self.products.list(limit)

    def open_product(self, index):
        self._guard_page()
        return self.products.open(index)

    def sort_products(self, mode):
        self._guard_page()
        return self.products.sort(mode)

    def filter_products(self, condition):
        self._guard_page()
        return self.products.filter(condition)
