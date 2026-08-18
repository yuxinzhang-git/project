from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import parse_qs, urlparse

from .browser import Browser, BrowserError


@dataclass
class PageContext:
    """A refreshed description of the page currently shown by Browser."""

    site: str | None = None
    page_type: str = "unknown"
    url: str = ""
    title: str = ""
    keyword: str | None = None
    channel_id: str | None = None
    user_id: str | None = None
    current_video_id: str | None = None
    current_item_id: str | None = None

    @classmethod
    def from_browser(cls, browser: Browser) -> "PageContext":
        try:
            state = browser.state()
        except BrowserError:
            return cls()
        return cls.from_state(state)

    @classmethod
    def from_state(cls, state: dict) -> "PageContext":
        url = state.get("url", "")
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        if "goofish.com" in host or "xianyu.com" in host:
            site = "xianyu"
        else:
            site = next((name for name in ("bilibili", "taobao", "baidu") if f"{name}.com" in host), None)
        query = parse_qs(parsed.query)
        keyword = (query.get("keyword") or query.get("q") or query.get("wd") or [None])[0]
        video_id = None
        item_id = None
        if site == "bilibili" and "/video/" in path:
            video_id = path.split("/video/", 1)[1].split("/", 1)[0]
        if site == "xianyu" and "/item" in path:
            item_id = (query.get("id") or [None])[0] or path.rsplit("/", 1)[-1]
        channel_parts = path.split("/")
        channel_id = None
        if site == "bilibili" and host.startswith("space.bilibili.com") and len(channel_parts) > 1:
            channel_id = channel_parts[1]
        elif site == "bilibili" and path.startswith("/space/") and len(channel_parts) > 2:
            channel_id = channel_parts[2]
        user_id = channel_id
        if site == "bilibili" and path.endswith("/favlist"):
            user_id = channel_id
        if video_id:
            page_type = "video"
        elif item_id:
            page_type = "item_detail"
        elif site == "bilibili" and path.endswith("/history"):
            page_type = "history"
        elif site == "bilibili" and path.endswith("/favlist"):
            page_type = "favorites"
        elif keyword is not None:
            page_type = "search"
        elif site:
            page_type = "home" if path in ("", "/") else "page"
        else:
            page_type = "unknown"
        return cls(site, page_type, url, state.get("title", ""), keyword, channel_id, user_id, video_id, item_id)

    def to_dict(self) -> dict:
        return asdict(self)
