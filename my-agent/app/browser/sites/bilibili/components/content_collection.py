from app.browser import BrowserError
from app.browser.components import ContentCollection


class BilibiliContentCollection(ContentCollection):
    CARD_SELECTORS = (".history-list .history-item", ".fav-list .small-item", ".bili-video-card")
    LINK_SELECTORS = ("a[href*='/video/']", "a")

    def __init__(self, browser):
        self.browser = browser

    def list(self, limit=20):
        for card in self.CARD_SELECTORS:
            for link in self.LINK_SELECTORS:
                try:
                    items = self.browser.card_links(card, link, limit=limit)
                except BrowserError:
                    continue
                results, seen = [], set()
                for item in items:
                    if "/video/" not in item["href"] or item["href"] in seen:
                        continue
                    seen.add(item["href"])
                    results.append({"index": len(results) + 1, "title": item["text"] or "untitled video", "url": item["href"]})
                if results:
                    return results
        raise BrowserError("Bilibili content collection was not found")

    def open(self, index):
        items = self.list(max(index, 20))
        if index < 1 or index > len(items):
            raise BrowserError(f"only found {len(items)} collection items")
        selected = items[index - 1]
        page = self.browser.open(selected["url"])
        return {"action": f"opened collection video {index}: {selected['title']}", "selected_result": selected, **page}
