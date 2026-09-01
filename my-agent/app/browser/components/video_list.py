class VideoList:
    """Small semantic interface for a list of videos."""

    def list(self, limit: int = 10) -> list[dict]:
        raise NotImplementedError

    def open(self, index: int) -> dict:
        raise NotImplementedError

    def play(self, index: int) -> dict:
        raise NotImplementedError
