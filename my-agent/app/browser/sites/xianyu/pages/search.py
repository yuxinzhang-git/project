class XianyuSearchPage:
    RESULT_CARDS = (
        "a[href*='/item?id=']",
        "a[href*='/item/']",
        "[class*='feeds-item']",
        "[class*='item-card']",
    )
    RESULT_LINKS = ("a[href*='/item?id=']", "a[href*='/item/']", "a")
    LOGIN_SELECTORS = (
        "[role='dialog']",
        "[class*='login']",
        "[class*='Login']",
        "[class*='modal']",
        "[class*='Modal']",
        "text=\u77ed\u4fe1\u767b\u5f55",
        "text=\u5bc6\u7801\u767b\u5f55",
        "text=\u624b\u673a\u626b\u7801\u5b89\u5168\u767b\u5f55",
    )
    LOGIN_TEXT_MARKERS = (
        "\u77ed\u4fe1\u767b\u5f55",
        "\u5bc6\u7801\u767b\u5f55",
        "\u624b\u673a\u626b\u7801\u5b89\u5168\u767b\u5f55",
        "\u8bf7\u8f93\u5165\u624b\u673a\u53f7",
        "\u83b7\u53d6\u9a8c\u8bc1\u7801",
    )
    NEXT_BUTTONS = (
        "text=\u4e0b\u4e00\u9875",
        "button:has-text('\u4e0b\u4e00\u9875')",
        "a:has-text('\u4e0b\u4e00\u9875')",
    )
    PREVIOUS_BUTTONS = (
        "text=\u4e0a\u4e00\u9875",
        "button:has-text('\u4e0a\u4e00\u9875')",
        "a:has-text('\u4e0a\u4e00\u9875')",
    )
