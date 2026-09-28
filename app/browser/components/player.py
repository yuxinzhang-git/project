class Player:
    """Small semantic interface for media playback controls."""

    def play(self) -> dict:
        raise NotImplementedError

    def pause(self) -> dict:
        raise NotImplementedError
