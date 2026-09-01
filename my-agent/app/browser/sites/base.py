from app.browser import Browser


class SiteAdapter:
    """Base class for site-specific actions built on the Browser facade."""

    def __init__(self, browser: Browser):
        self.browser = browser

