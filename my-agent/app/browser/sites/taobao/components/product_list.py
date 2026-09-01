from ..errors import TaobaoPageStructureError


class TaobaoProductList:
    CARD_SELECTORS = ("[data-spm='item']", ".items .item", ".宝贝列表 .item", "[class*='item']")
    LINK_SELECTORS = ("a[href*='item.taobao.com']", "a[href*='detail.tmall.com']", "a[href*='/item.htm']", "a")

    def __init__(self, browser):
        self.browser = browser

    def list(self, limit=20):
        for card in self.CARD_SELECTORS:
            for link in self.LINK_SELECTORS:
                try:
                    items = self.browser.card_links(card, link, limit=limit)
                except Exception:
                    continue
                results = []
                seen = set()
                for item in items:
                    if item["href"] in seen or "item" not in item["href"]:
                        continue
                    seen.add(item["href"])
                    results.append({"index": len(results) + 1, "title": item["text"] or "untitled product", "url": item["href"]})
                if results:
                    return results
        raise TaobaoPageStructureError("Taobao product cards were not found; page structure may have changed")

    def open(self, index):
        products = self.list(max(index, 20))
        if index < 1 or index > len(products):
            raise TaobaoPageStructureError(f"only found {len(products)} products")
        selected = products[index - 1]
        page = self.browser.open(selected["url"])
        return {"action": f"opened product {index}: {selected['title']}", "selected_product": selected, **page}

    def sort(self, mode):
        labels = {"sales": "销量", "price": "价格", "default": "综合"}
        label = labels.get(mode.lower(), mode)
        try:
            result = self.browser.click(f"text={label}")
        except Exception as exc:
            raise TaobaoPageStructureError(f"sort control '{mode}' was not found") from exc
        return {**result, "action": f"sorted products by {mode}"}

    def filter(self, condition):
        try:
            result = self.browser.click(f"text={condition}")
        except Exception as exc:
            raise TaobaoPageStructureError(f"filter control '{condition}' was not found") from exc
        return {**result, "action": f"filtered products by {condition}"}
