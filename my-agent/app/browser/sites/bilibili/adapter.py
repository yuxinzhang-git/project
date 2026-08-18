from .actions import BilibiliActions
from .components import BilibiliContentActions, BilibiliContentCollection, BilibiliPagination
from .navigation import BilibiliNavigation


class BilibiliAdapter:
    """Bilibili site facade composed of navigation and page actions."""

    def __init__(self, browser):
        self.browser = browser
        self.navigation = BilibiliNavigation(browser)
        self.actions = BilibiliActions(browser)
        self.pagination = BilibiliPagination(browser)
        self.content_actions = BilibiliContentActions(browser)
        self.collection = BilibiliContentCollection(browser)

    def capability(self):
        from .capability import capability
        return capability()

    # Compatibility methods keep existing callers stable while exposing the
    # navigation/actions split to new code.
    def open_home(self):
        return self.navigation.open_home()

    def search(self, keyword):
        return self.navigation.search(keyword)

    def list_results(self, limit=10):
        return self.actions.list_videos(limit)

    def open_result(self, index):
        return self.actions.open_video(index)

    def open_selected(self, selected, index):
        return self.actions.open_selected(selected, index)

    def play_result(self, index):
        return self.actions.play_video(index)

    def play_selected(self, selected, index):
        return self.actions.play_selected(selected, index)

    def pause_current(self):
        return self.actions.pause_current_video()

    def play_current(self):
        return self.actions.player.play()

    def open_current(self):
        return self.actions.open_current_video()

    def play_relative(self, offset):
        return self.actions.play_relative(offset)

    def open_history(self):
        return self.navigation.open_history()

    def next_page(self):
        return self.pagination.next()

    def previous_page(self):
        return self.pagination.previous()

    def goto_page(self, page):
        return self.pagination.goto(page)

    def like(self):
        return self.content_actions.like()

    def unlike(self):
        return self.content_actions.unlike()

    def coin(self, count=1):
        return self.content_actions.coin(count)

    def favorite(self):
        return self.content_actions.favorite()

    def unfavorite(self):
        return self.content_actions.unfavorite()

    def list_collection(self, limit=20):
        return self.collection.list(limit)

    def open_collection_item(self, index):
        return self.collection.open(index)
