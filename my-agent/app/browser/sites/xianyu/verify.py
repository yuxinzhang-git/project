from pathlib import Path

from app.browser import Browser, BrowserError, PageContext
from app.browser.sites.xianyu.adapter import XianyuAdapter
from app.browser.sites.xianyu.errors import (
    XianyuBrowserError,
    XianyuLoginRequiredError,
    XianyuPageStructureError,
    XianyuRiskControlError,
)
from app.services.smart_operation import SmartOperationService


KEYWORD = "二手相机"
SCREENSHOT = Path("data/xianyu-verification.png")


def _report_error(stage, exc):
    if isinstance(exc, XianyuLoginRequiredError):
        category = "login"
    elif isinstance(exc, XianyuRiskControlError):
        category = "risk_control_or_captcha"
    elif isinstance(exc, XianyuPageStructureError):
        category = "page_structure"
    elif isinstance(exc, (BrowserError, XianyuBrowserError)):
        category = "browser_playwright_network"
    else:
        category = type(exc).__name__
    print(f"stage={stage} error_type={category} error={exc}")


def main():
    browser = Browser(headless=True)
    try:
        adapter = XianyuAdapter(browser)
        service = SmartOperationService(browser)
        print("intent_home=", service._parse_command("打开咸鱼首页"))
        print("intent_search=", service._parse_command("搜索咸鱼 二手相机"))
        print("intent_list=", service._parse_command("咸鱼商品列表"))
        print("intent_open=", service._parse_command("咸鱼打开第 1 个商品"))
        print("intent_next=", service._parse_command("咸鱼下一页"))
        for stage, operation in (
            ("open_home", adapter.open_home),
            ("search", lambda: adapter.search(KEYWORD)),
            ("list_items", adapter.list_items),
            ("open_first_item", lambda: adapter.open_item(1)),
        ):
            try:
                print(f"stage={stage} ok={operation()}")
            except Exception as exc:
                _report_error(stage, exc)
        try:
            print("context=", PageContext.from_browser(browser).to_dict())
            print("screenshot=", browser.screenshot(SCREENSHOT))
        except Exception as exc:
            _report_error("final_state", exc)
    finally:
        browser.close()


if __name__ == "__main__":
    main()
