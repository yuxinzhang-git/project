class SearchBox:
    """Small semantic interface for a site search box."""

    def search(self, keyword: str) -> dict:
        raise NotImplementedError
