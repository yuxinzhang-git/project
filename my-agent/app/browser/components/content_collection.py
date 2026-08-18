class ContentCollection:
    """Semantic interface for history, favorites, and playlists."""

    def list(self, limit: int = 20) -> list[dict]:
        raise NotImplementedError

    def open(self, index: int) -> dict:
        raise NotImplementedError
