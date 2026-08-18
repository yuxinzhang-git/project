from .actions import XianyuActions
from .errors import XianyuBrowserError, XianyuLoginRequiredError, XianyuRiskControlError
from .navigation import XianyuNavigation


class XianyuAdapter:
    """Stable Xianyu facade for read-only navigation and listing actions."""

    def __init__(self, browser):
        self.browser = browser
        self.navigation = XianyuNavigation(browser)
        self.actions = XianyuActions(browser)

    def capability(self):
        from .capability import capability
        return capability()

    def _guard_page(self):
        state = self.browser.state()
        if state.get("url", "").startswith("chrome-error://"):
            raise XianyuBrowserError("the browser is showing a network error page")
        marker = f"{state.get('title', '')} {state.get('url', '')}".lower()
        risk_markers = ("captcha", "verify", "security", "slider", "滑块", "验证码", "风控", "安全验证")
        login_markers = ("login", "sign in", "登录", "请登录")
        if any(word in marker for word in risk_markers):
            raise XianyuRiskControlError("Xianyu risk control or verification is blocking this operation; no bypass was attempted")
        if any(word in marker for word in login_markers):
            raise XianyuLoginRequiredError("Xianyu login is required for this operation")
        self.actions.ensure_page_ready()

    def open_home(self):
        return self.navigation.open_home()

    def search(self, keyword):
        return self.navigation.search(keyword)

    def back(self):
        return self.navigation.back()

    def list_items(self, limit=20):
        self._guard_page()
        return self.actions.list_items(limit)

    def open_item(self, index):
        self._guard_page()
        return self.actions.open_item(index)

    def next_page(self):
        self._guard_page()
        return self.actions.next_page()

    def previous_page(self):
        self._guard_page()
        return self.actions.previous_page()

    def estimate_items(self, items):
        return self.actions.estimate_items(items)
