CAPABILITY = {
    "site": "taobao",
    "navigation": ["home", "search", "favorites", "back"],
    "page_actions": ["list_products", "open_product", "sort", "filter"],
    "objects": ["product", "product_list"],
}


def capability():
    return {key: list(value) if isinstance(value, list) else value for key, value in CAPABILITY.items()}
