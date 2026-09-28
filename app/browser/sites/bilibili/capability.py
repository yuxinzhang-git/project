CAPABILITY = {
    "site": "bilibili",
    "navigation": ["home", "search", "channel", "favorites", "history", "back"],
    "page_actions": [
        "list", "open_item", "play", "pause", "play_relative", "open_current",
        "pagination_next", "pagination_previous", "pagination_goto",
        "like", "unlike", "coin", "favorite", "unfavorite",
    ],
    "objects": ["video", "player", "search_box", "pagination", "content_actions", "content_collection"],
}


def capability():
    return {key: list(value) if isinstance(value, list) else value for key, value in CAPABILITY.items()}
