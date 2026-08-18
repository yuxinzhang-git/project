from pydantic import BaseModel


class BrowserOpenRequest(BaseModel):
    url: str


class BrowserSearchRequest(BaseModel):
    keyword: str


class BrowserLocatorRequest(BaseModel):
    locator: str


class BrowserTypeRequest(BrowserLocatorRequest):
    text: str


class BrowserScreenshotRequest(BaseModel):
    filename: str = "latest.png"

