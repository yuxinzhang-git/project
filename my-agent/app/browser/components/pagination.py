class Pagination:
    """Semantic interface for paged content."""

    def next(self) -> dict:
        raise NotImplementedError

    def previous(self) -> dict:
        raise NotImplementedError

    def goto(self, page: int) -> dict:
        raise NotImplementedError
