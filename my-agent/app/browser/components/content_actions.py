class ContentActions:
    """Semantic actions that can be performed on the current content."""

    def like(self) -> dict:
        raise NotImplementedError

    def unlike(self) -> dict:
        raise NotImplementedError

    def coin(self, count: int = 1) -> dict:
        raise NotImplementedError

    def favorite(self) -> dict:
        raise NotImplementedError

    def unfavorite(self) -> dict:
        raise NotImplementedError
