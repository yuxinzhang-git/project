import re

from app.browser import Browser, BrowserError, PageContext
from app.browser.sites import BilibiliAdapter, TaobaoAdapter, XianyuAdapter
from app.browser.sites.taobao.errors import TaobaoPageStructureError, TaobaoRiskControlError


class SmartOperationError(RuntimeError):
    pass


class SmartOperationService:
    """Rule-based natural language parser and site adapter dispatcher."""

    SITE_ALIASES = {
        "xianyu": "xianyu", "goofish": "xianyu", "咸鱼": "xianyu",
        "bilibili": "bilibili", "哔哩哔哩": "bilibili", "b站": "bilibili",
        "taobao": "taobao", "淘宝": "taobao",
        "baidu": "baidu", "百度": "baidu",
    }
    SITE_URLS = {"bilibili": "https://www.bilibili.com", "taobao": "https://www.taobao.com", "baidu": "https://www.baidu.com", "xianyu": "https://www.goofish.com/"}
    NUMBER_WORDS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

    def __init__(self, browser: Browser):
        self.browser = browser
        self.bilibili = BilibiliAdapter(browser)
        self.taobao = TaobaoAdapter(browser)
        self.xianyu = XianyuAdapter(browser)
        self._results = {"bilibili": [], "taobao": [], "xianyu": []}
        self._current_index = {"bilibili": None, "taobao": None, "xianyu": None}

    def execute(self, command: str) -> dict:
        plan = self._parse_command(command)
        context = PageContext.from_browser(self.browser)
        site = plan.get("site") or context.site
        if not site:
            raise SmartOperationError("please specify a supported site first")
        if context.site == "xianyu" and plan.get("site") in (None, "taobao"):
            if plan.get("target") == "product":
                plan["target"] = "item"
            plan["site"] = "xianyu"
            site = "xianyu"
        plan["site"] = site
        if site not in ("bilibili", "taobao", "baidu", "xianyu"):
            raise SmartOperationError(f"unsupported site: {site}")
        initial = context.to_dict()
        result = self._dispatch(plan, context)
        try:
            inspected = self.browser.interactive_elements()
        except BrowserError:
            inspected = []
        return {
            "command": command.strip(), "plan": plan, "action": result.get("action", plan["action"]),
            "title": result.get("title", ""), "url": result.get("url", ""),
            "initial_page": initial, "context": PageContext.from_browser(self.browser).to_dict(),
            "results": result.get("results", self._results.get(site, [])),
            "inspected_elements": [{"label": x["label"], "kind": x["kind"], "type": x["type"]} for x in inspected],
            "inspected_count": len(inspected),
        }

    def estimate_xianyu(self, keyword: str) -> dict:
        if not keyword or not keyword.strip():
            raise SmartOperationError("Xianyu estimate keyword cannot be empty")
        result = self.execute(f"搜索咸鱼 {keyword.strip()}")
        estimate = self.xianyu.estimate_items(result.get("results", []))
        return {**result, "estimate": estimate, "action": f"estimated Xianyu prices: {keyword.strip()}"}

    def _dispatch(self, plan, context):
        site, target, action = plan["site"], plan["target"], plan["action"]
        if site == "baidu":
            if target == "search":
                return self.browser.search(plan["keyword"])
            raise SmartOperationError("only search is supported for Baidu")
        adapter = self.bilibili if site == "bilibili" else self.taobao if site == "taobao" else self.xianyu
        if plan.get("keyword") and not (target == "search" and action == "open"):
            adapter.search(plan["keyword"])
        if target == "search" and action == "open":
            result = adapter.search(plan["keyword"])
            self._results[site] = adapter.actions.list_videos() if site == "bilibili" else adapter.list_products() if site == "taobao" else adapter.list_items()
            return {**result, "results": self._results[site], "action": f"searched {site}: {plan['keyword']}"}
        if target == "home" and action == "open":
            return adapter.open_home()
        if target == "favorites" and action == "open":
            if site == "bilibili":
                return adapter.navigation.open_favorites(plan.get("user_id") or "")
            return adapter.open_favorites()
        if target == "channel" and action == "open":
            return adapter.navigation.open_channel(plan["channel_id"])
        if target == "back":
            return adapter.navigation.back() if site == "bilibili" else adapter.back()
        if site == "bilibili" and target == "history" and action == "open":
            return adapter.open_history()
        if site == "bilibili" and target == "pagination":
            if action == "next":
                return adapter.next_page()
            if action == "previous":
                return adapter.previous_page()
            if action == "goto":
                return adapter.goto_page(plan["page"])
        if site == "bilibili":
            if target == "video" and action == "open_current":
                return adapter.open_current()
            if target == "video" and action == "play" and plan.get("relative"):
                result = adapter.play_relative(plan["relative"])
                return result
            if target == "video" and action == "open":
                result = adapter.open_result(plan["index"])
                self._current_index[site] = plan["index"]
                return result
            if target == "video" and action == "play":
                if plan.get("index") is None:
                    return adapter.play_current()
                result = adapter.play_result(plan["index"])
                self._current_index[site] = plan["index"]
                return result
            if target == "video" and action == "list":
                return {"title": context.title, "url": context.url, "results": adapter.list_results(), "action": "listed videos"}
            if target == "video" and action == "pause":
                return adapter.pause_current()
            if target == "video" and action == "like":
                return adapter.like()
            if target == "video" and action == "unlike":
                return adapter.unlike()
            if target == "video" and action == "coin":
                return adapter.coin(plan["count"])
            if target == "video" and action == "favorite":
                return adapter.favorite()
            if target == "video" and action == "unfavorite":
                return adapter.unfavorite()
        if site == "taobao":
            if target == "product" and action == "list":
                return {"title": context.title, "url": context.url, "results": adapter.list_products(), "action": "listed products"}
            if target == "product" and action == "open":
                return adapter.open_product(plan["index"])
            if target == "product" and action == "sort":
                return adapter.sort_products(plan["mode"])
            if target == "product" and action == "filter":
                return adapter.filter_products(plan["condition"])
        if site == "xianyu":
            if target == "item" and action == "list":
                return {"title": context.title, "url": context.url, "results": adapter.list_items(), "action": "listed Xianyu items"}
            if target == "item" and action == "open":
                return adapter.open_item(plan["index"])
            if target == "pagination" and action == "next":
                return adapter.next_page()
            if target == "pagination" and action == "previous":
                return adapter.previous_page()
        raise SmartOperationError(f"unsupported operation: {site}/{target}/{action}")

    def _parse_command(self, command):
        text = command.strip()
        if not text:
            raise SmartOperationError("command cannot be empty")
        site = self._site_in(text)
        if site == "xianyu" or "咸鱼" in text or "goofish" in text.lower():
            return self._parse_xianyu_command(text)
        if re.search(r"(?:打开|进入|open)\s*(?:淘宝|taobao)(?:首页|home)?$", text, re.I) or re.fullmatch(r"(?:打开|进入|open)\s*(?:哔哩哔哩|b站|bilibili)(?:首页|home)?", text, re.I):
            return self._plan("navigation", "home", "open", site=site)
        if re.search(r"(?:返回|back)", text, re.I):
            if re.search(r"(?:返回主界面|回到主界面|返回.*(?:Bilibili|B站).*(?:首页|主界面)|back to home)", text, re.I):
                return self._plan("navigation", "home", "open", site=site or "bilibili")
            return self._plan("navigation", "back", "open", site=site)
        search = re.search(r"(?:搜索|search)\s*(.+)$", text, re.I)
        if search:
            raw_keyword = search.group(1).strip()
            trailing = re.search(r"[，,。]?\s*(打开|播放|open|play)\s*第\s*(\d+|[一二两三四五六七八九十])\s*(?:个)?\s*(视频|video)?$", raw_keyword, re.I)
            if trailing:
                keyword = raw_keyword[:trailing.start()].rstrip(" ，,。")
                return self._plan("page_action", "video", "play" if trailing.group(1) in ("播放", "play") else "open", site=site, keyword=keyword, index=self._parse_index(trailing.group(2)))
            keyword = re.sub(r"^(?:在)?(?:淘宝|taobao|哔哩哔哩|b站|bilibili)\s*", "", raw_keyword, flags=re.I).strip()
            return self._plan("navigation", "search", "open", site=site, keyword=keyword)
        sort = re.search(r"(?:按|sort\s+by)\s*(销量|价格|综合|sales|price|default).*", text, re.I)
        if sort:
            return self._plan("page_action", "product", "sort", site=site or "taobao", mode=sort.group(1))
        filter_match = re.search(r"(?:筛选|filter)\s*(.+)$", text, re.I)
        if filter_match:
            return self._plan("page_action", "product", "filter", site=site or "taobao", condition=filter_match.group(1).strip())
        if re.search(r"(?:下一个|next)", text, re.I):
            return self._plan("page_action", "video", "play", site=site, relative=1)
        if re.search(r"(?:上一个|previous|prev)", text, re.I):
            return self._plan("page_action", "video", "play", site=site, relative=-1)
        if re.search(r"(?:当前视频|current video)", text, re.I):
            if re.search(r"(?:继续播放|恢复播放|resume|play current|播放当前)", text, re.I):
                return self._plan("page_action", "video", "play", site=site)
            return self._plan("page_action", "video", "open_current", site=site)
        index_match = re.search(r"(?:第\s*)?(\d+|[一二两三四五六七八九十])\s*(?:个)?\s*(视频|商品|video|product)?", text, re.I)
        if index_match and re.search(r"(?:打开|播放|open|play)", text, re.I):
            target = "product" if re.search(r"商品|product", text, re.I) or site == "taobao" else "video"
            action = "play" if re.search(r"播放|play", text, re.I) else "open"
            return self._plan("page_action", target, action, site=site, index=self._parse_index(index_match.group(1)))
        if re.search(r"(?:商品列表|list products)", text, re.I):
            return self._plan("page_action", "product", "list", site=site or "taobao")
        if re.search(r"(?:视频列表|list videos)", text, re.I):
            return self._plan("page_action", "video", "list", site=site or "bilibili")
        if re.search(r"(?:继续播放|恢复播放|resume)", text, re.I):
            return self._plan("page_action", "video", "play", site=site)
        if re.search(r"(?:暂停|pause)", text, re.I):
            return self._plan("page_action", "video", "pause", site=site)
        if re.search(r"(?:返回主界面|回到主界面|返回.*(?:Bilibili|B站).*(?:首页|主界面)|back to home)", text, re.I):
            return self._plan("navigation", "home", "open", site=site or "bilibili")
        if re.search(r"(?:下一页|next page)", text, re.I):
            return self._plan("page_action", "pagination", "next", site=site)
        if re.search(r"(?:上一页|previous page|prev page)", text, re.I):
            return self._plan("page_action", "pagination", "previous", site=site)
        page_match = re.search(r"(?:第\s*)(\d+)\s*(?:页|page)", text, re.I)
        if page_match:
            return self._plan("page_action", "pagination", "goto", site=site, page=int(page_match.group(1)))
        if re.search(r"(?:打开|进入|查看).*(?:历史|history)", text, re.I):
            return self._plan("navigation", "history", "open", site=site or "bilibili")
        if re.search(r"(?:打开|进入|查看).*(?:收藏夹|favorites?)", text, re.I):
            return self._plan("navigation", "favorites", "open", site=site or "bilibili")
        if re.search(r"(?:取消点赞|unlike)", text, re.I):
            return self._plan("page_action", "video", "unlike", site=site)
        if re.search(r"(?:点赞|like)", text, re.I):
            return self._plan("page_action", "video", "like", site=site)
        if re.search(r"(?:取消收藏|unfavorite)", text, re.I):
            return self._plan("page_action", "video", "unfavorite", site=site)
        if re.search(r"(?:收藏|favorite)", text, re.I):
            return self._plan("page_action", "video", "favorite", site=site)
        coin_match = re.search(r"(?:投币|投\s*(\d+|一|二)\s*个币|coin)\s*(?:(\d+|一|二)\s*(?:个)?(?:币|coins?)?)?", text, re.I)
        if coin_match:
            raw_count = coin_match.group(1) or coin_match.group(2) or "1"
            count = {"一": 1, "二": 2}.get(raw_count, int(raw_count) if raw_count.isdigit() else 1)
            return self._plan("page_action", "video", "coin", site=site, count=count)
        raise SmartOperationError("command not recognized")

    def _parse_xianyu_command(self, text):
        if re.search(r"(打开|进入|open).*(咸鱼|xianyu|goofish).*(首页|home)?$", text, re.I):
            return self._plan("navigation", "home", "open", site="xianyu")
        if re.search(r"(返回|back)", text, re.I):
            return self._plan("navigation", "back", "open", site="xianyu")
        if re.search(r"(下一页|next page)", text, re.I):
            return self._plan("page_action", "pagination", "next", site="xianyu")
        if re.search(r"(上一页|previous page|prev page)", text, re.I):
            return self._plan("page_action", "pagination", "previous", site="xianyu")
        search = re.search(r"(?:搜索|search)\s*(?:咸鱼|xianyu|goofish)?\s*(.+)$", text, re.I)
        if search:
            return self._plan("navigation", "search", "open", site="xianyu", keyword=search.group(1).strip())
        if re.search(r"(商品列表|物品列表|list items|list products)", text, re.I):
            return self._plan("page_action", "item", "list", site="xianyu")
        match = re.search(r"(?:打开|查看|open)\s*(?:第\s*)?(\d+)\s*(?:个|件)?\s*(?:商品|物品|item|product)?", text, re.I)
        if match:
            return self._plan("page_action", "item", "open", site="xianyu", index=int(match.group(1)))
        raise SmartOperationError("unrecognized Xianyu operation")

    def _site_in(self, text):
        for alias, site in self.SITE_ALIASES.items():
            if re.search(re.escape(alias), text, re.I):
                return site
        return None

    def _plan(self, category, target, action, **values):
        plan = {"category": category, "target": target, "action": action, **values}
        plan.setdefault("site", None)
        plan.setdefault("index", None)
        plan.setdefault("relative", None)
        plan.setdefault("keyword", None)
        return plan

    def _parse_index(self, value):
        return int(value) if value.isdigit() else self.NUMBER_WORDS.get(value, 1)
