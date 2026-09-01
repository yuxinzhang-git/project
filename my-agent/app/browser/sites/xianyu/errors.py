class XianyuError(RuntimeError):
    """Base error for Xianyu operations."""


class XianyuLoginRequiredError(XianyuError):
    """The current operation requires an authenticated Xianyu session."""


class XianyuRiskControlError(XianyuError):
    """Xianyu verification or risk control is blocking the operation."""


class XianyuPageStructureError(XianyuError):
    """Expected Xianyu controls or result cards were not found."""


class XianyuBrowserError(XianyuError):
    """Browser, Playwright, configuration, or network failure."""
