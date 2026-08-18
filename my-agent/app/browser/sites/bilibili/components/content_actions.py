from app.browser import BrowserError
from app.browser.components import ContentActions


class BilibiliContentActions(ContentActions):
    LIKE_CONTROLS = ("button[aria-label*='点赞']", ".video-like", ".video-toolbar .like")
    UNLIKE_CONTROLS = ("button[aria-pressed='true'][aria-label*='点赞']", ".video-like.on", ".video-toolbar .like.on")
    FAVORITE_CONTROLS = ("button[aria-label*='收藏']", ".video-fav", ".video-toolbar .favorite")
    UNFAVORITE_CONTROLS = ("button[aria-pressed='true'][aria-label*='收藏']", ".video-fav.on", ".video-toolbar .favorite.on")
    COIN_CONTROLS = ("button[aria-label*='投币']", ".video-coin", ".video-toolbar .coin")
    COIN_CONFIRM_CONTROLS = ("button:has-text('确定')", "button:has-text('确认')", "text=确定")
    DEFAULT_FAVORITE_CONTROLS = ("label:has-text('默认收藏夹')", ".fav-item:has-text('默认收藏夹')", "text=默认收藏夹")
    FAVORITE_CONFIRM_CONTROLS = ("button:has-text('确定')", "button:has-text('确认')", "text=确定")

    def __init__(self, browser):
        self.browser = browser

    def _click_any(self, controls, action):
        for locator in controls:
            try:
                return {**self.browser.click(locator), "action": action}
            except BrowserError:
                continue
        raise BrowserError(f"Bilibili {action} control was not found; login or page state may be required")

    def like(self):
        return self._click_any(self.LIKE_CONTROLS, "liked current video")

    def unlike(self):
        return self._click_any(self.UNLIKE_CONTROLS, "unliked current video")

    def coin(self, count=1):
        if count not in (1, 2):
            raise BrowserError("Bilibili supports sending 1 or 2 coins")
        result = self._click_any(self.COIN_CONTROLS, "opened coin control")
        if count == 2:
            result = {**result, **self._click_any((".coin-item:has-text('2硬币')", "button:has-text('2硬币')", "text=2硬币"), "selected 2 coins")}
        else:
            try:
                result = {**result, **self._click_any((".coin-item:has-text('1硬币')", "button:has-text('1硬币')", "text=1硬币"), "selected 1 coin")}
            except BrowserError:
                pass
        try:
            result = {**result, **self._click_any(self.COIN_CONFIRM_CONTROLS, "confirmed coin submission")}
        except BrowserError:
            # Some Bilibili layouts submit as soon as the coin count is selected.
            pass
        return {**result, "action": f"sent {count} coin(s) to current video"}

    def favorite(self):
        result = self._click_any(self.FAVORITE_CONTROLS, "opened favorite dialog")
        result = {**result, **self._click_any(self.DEFAULT_FAVORITE_CONTROLS, "selected default favorite folder")}
        result = {**result, **self._click_any(self.FAVORITE_CONFIRM_CONTROLS, "confirmed favorite")}
        return {**result, "action": "favorited current video in the default folder"}

    def unfavorite(self):
        result = self._click_any(self.UNFAVORITE_CONTROLS, "opened favorite dialog")
        result = {**result, **self._click_any(self.DEFAULT_FAVORITE_CONTROLS, "unselected default favorite folder")}
        result = {**result, **self._click_any(self.FAVORITE_CONFIRM_CONTROLS, "confirmed favorite removal")}
        return {**result, "action": "removed current video from the default favorite folder"}
