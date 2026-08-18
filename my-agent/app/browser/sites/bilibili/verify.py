from pathlib import Path

from app.browser import Browser, BrowserError


TARGET_URL = "https://www.bilibili.com"
SCREENSHOT = Path("data/bilibili-verification.png")


def main() -> None:
    SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    try:
        browser = Browser(headless=True)
        try:
            page = browser.open(TARGET_URL)
            browser.screenshot(SCREENSHOT)
            print(f"title={page['title']}")
            print(f"url={page['url']}")
            print(f"screenshot={SCREENSHOT}")
        finally:
            browser.close()
    except BrowserError as exc:
        print("error_type=Browser/Edge")
        print(f"error={exc}")
        raise


if __name__ == "__main__":
    main()
