from app.browser import BrowserError

from ..errors import XianyuLoginRequiredError, XianyuPageStructureError
from .market_data import XianyuMarketData
from ..pages.search import XianyuSearchPage


class XianyuItemList:
    def __init__(self, browser):
        self.browser = browser

    def ensure_ready(self):
        """Raise a classified login error before card parsing starts."""
        for locator in XianyuSearchPage.LOGIN_SELECTORS:
            try:
                visible_text = " ".join(self.browser.texts(locator, limit=5))
            except BrowserError:
                continue
            if any(marker in visible_text for marker in XianyuSearchPage.LOGIN_TEXT_MARKERS):
                raise XianyuLoginRequiredError(
                    "Xianyu login is required; the login dialog is blocking the search results"
                )

    def list(self, limit=20):
        self.ensure_ready()
        for card in XianyuSearchPage.RESULT_CARDS:
            for link in XianyuSearchPage.RESULT_LINKS:
                try:
                    items = self.browser.card_links(card, link, limit=limit)
                except BrowserError:
                    continue
                results, seen = [], set()
                for item in items:
                    href = item["href"]
                    if href in seen or "/item" not in href:
                        continue
                    seen.add(href)
                    parsed = XianyuMarketData.normalize_item(item)
                    parsed.update({"index": len(results) + 1, "url": href})
                    results.append(parsed)
                    if len(results) >= limit:
                        break
                if results:
                    return results

        # Goofish may render the whole card as a link and change the card
        # wrapper class without changing the item URL. Keep a broad, read-only
        # link fallback so card parsing is not coupled to a wrapper class.
        try:
            links = self.browser.links("a[href]", limit=max(limit * 8, 100))
        except BrowserError:
            links = []
        results, seen = [], set()
        for item in links:
            href = item.get("href", "")
            if not self._is_item_href(href) or href in seen:
                continue
            seen.add(href)
            text = item.get("text", "").strip()
            parsed = XianyuMarketData.normalize_item({"text": text, "card_text": text})
            parsed.update({"index": len(results) + 1, "url": href})
            results.append(parsed)
            if len(results) >= limit:
                return results
        if results:
            return results
        raise XianyuPageStructureError(
            "Xianyu item cards were not found; page structure may have changed"
        )

    @staticmethod
    def _is_item_href(href):
        value = (href or "").lower()
        return any(marker in value for marker in ("/item", "itemid=", "item_id=", "/detail"))

    def open(self, index):
        if index < 1:
            raise BrowserError("index must be at least 1")
        items = self.list(max(index, 20))
        if index > len(items):
            raise XianyuPageStructureError(f"only found {len(items)} items")
        selected = items[index - 1]
        page = self.browser.open(selected["url"])
        return {"action": f"opened item {index}: {selected['title']}", "selected_item": selected, **page}
