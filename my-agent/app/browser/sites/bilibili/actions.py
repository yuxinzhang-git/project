from urllib.parse import urlparse

from app.browser import BrowserError
from app.browser.components import Player, VideoList


class BilibiliVideoList(VideoList):
    RESULT_CARDS = ".bili-video-card"
    RESULT_TITLE_LINK = "a[href*='/video/']:has(.bili-video-card__info--tit)"
    RESULT_TITLE_TEXT = ".bili-video-card__info--tit"
    FALLBACK_RESULT_TITLE_LINK = "a[href*='/video/']"

    def __init__(self, browser):
        self.browser = browser

    def list(self, limit=10):
        items = self.browser.card_links(self.RESULT_CARDS, self.RESULT_TITLE_LINK, self.RESULT_TITLE_TEXT)
        if not items:
            items = self.browser.card_links(self.RESULT_CARDS, self.FALLBACK_RESULT_TITLE_LINK)
        results, seen = [], set()
        for item in items:
            href = item["href"]
            markers = f"{item.get('card_class', '')} {item.get('card_aria', '')} {item.get('text', '')}".lower()
            if "/video/" not in href or href in seen or any(x in markers for x in ("ad-card", "bili-video-card--ad", "advertisement")):
                continue
            seen.add(href)
            results.append({"index": len(results) + 1, "title": item["text"] or "untitled video", "url": href})
            if len(results) >= limit:
                break
        return results

    def open(self, index):
        videos = self.list(max(index, 10))
        if index < 1 or index > len(videos):
            raise BrowserError(f"only found {len(videos)} videos")
        selected = videos[index - 1]
        page = self.browser.open(selected["url"])
        return {"action": f"opened video {index}: {selected['title']}", "selected_result": selected, **page}

    def play(self, index):
        result = self.open(index)
        return BilibiliPlayer(self.browser)._play_opened(result, index)


class BilibiliPlayer(Player):
    PLAY_CONTROLS = (".bpx-player-ctrl-play", "button[aria-label*='播放']", ".bilibili-player-video-btn-start")

    def __init__(self, browser):
        self.browser = browser

    def _play_opened(self, result, index):
        for locator in self.PLAY_CONTROLS:
            try:
                clicked = self.browser.click(locator)
                return {**result, **clicked, "action": f"playing video {index}: {result['selected_result']['title']}"}
            except BrowserError:
                continue
        return {**result, "action": f"opened video {index}; page controls playback", "play_control_found": False}

    def play(self):
        state = self.browser.state()
        for locator in self.PLAY_CONTROLS:
            try:
                return {**self.browser.click(locator), "action": "playing current video"}
            except BrowserError:
                continue
        raise BrowserError(f"player control not found on {state['url']}")

    def pause(self):
        state = self.browser.state()
        for locator in (".bpx-player-ctrl-pause", "button[aria-label*='Pause']", "button[aria-label*='暂停']", ".bpx-player-ctrl-play"):
            try:
                return {**self.browser.click(locator), "action": "paused current video"}
            except BrowserError:
                continue
        raise BrowserError(f"pause control not found on {state['url']}")


class BilibiliActions:
    """Compatibility facade backed by semantic page components."""

    def __init__(self, browser):
        self.browser = browser
        self.video_list = BilibiliVideoList(browser)
        self.player = BilibiliPlayer(browser)

    def list_videos(self, limit=10):
        return self.video_list.list(limit)

    def open_video(self, index):
        return self.video_list.open(index)

    def open_selected(self, selected, index):
        page = self.browser.open(selected["url"])
        return {"action": f"opened video {index}: {selected['title']}", "selected_result": selected, **page}

    def play_video(self, index):
        return self.video_list.play(index)

    def pause_current_video(self):
        return self.player.pause()

    def play_selected(self, selected, index):
        result = self.open_selected(selected, index)
        return self.player._play_opened(result, index)

    def open_current_video(self):
        state = self.browser.state()
        if "/video/" not in urlparse(state["url"]).path:
            raise BrowserError("current page is not a Bilibili video page")
        return {"action": "opened current video", **state}

    def play_relative(self, offset):
        if offset not in (-1, 1):
            raise BrowserError("only previous (-1) and next (1) are supported")
        current = self.browser.state()["url"]
        if "/video/" not in urlparse(current).path:
            raise BrowserError("open a Bilibili video before relative playback")
        self.browser.back()
        videos = self.list_videos(100)
        current_index = next((x["index"] for x in videos if x["url"].rstrip("/") == current.rstrip("/")), None)
        if current_index is None or not 1 <= current_index + offset <= len(videos):
            raise BrowserError("current video is not in the result list or is at its boundary")
        return self.play_selected(videos[current_index + offset - 1], current_index + offset)
