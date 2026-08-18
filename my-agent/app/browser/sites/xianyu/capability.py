CAPABILITY = {
    "site": "xianyu",
    "intent_categories": ["navigation", "page_action"],
    "navigation": ["home", "search", "back"],
    "page_actions": ["list_items", "open_item", "next_page", "previous_page", "estimate_items"],
    "objects": ["item", "item_list", "market_data", "pagination"],
    "side_effect_actions": [],
}


def capability():
    return {key: list(value) if isinstance(value, list) else value for key, value in CAPABILITY.items()}
