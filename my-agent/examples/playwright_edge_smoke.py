from app.browser import Browser


def main() -> None:
    browser = Browser(headless=True)
    try:
        page = browser.open("https://example.com")
        print(f"title={page['title']}")
        print(f"h1={browser.text('h1')}")
    finally:
        browser.close()


if __name__ == "__main__":
    main()
