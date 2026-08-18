import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, Query

from app.browser import Browser, BrowserError
from app.config import settings
from app.schemas.browser import BrowserLocatorRequest, BrowserOpenRequest, BrowserScreenshotRequest, BrowserSearchRequest, BrowserTypeRequest

router = APIRouter(prefix="/api/browser", tags=["browser"])
browser = Browser(profile_dir=settings.browser_profile_dir)
_browser_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="browser-api")


def run_browser_operation(operation):
    return _browser_executor.submit(operation).result()


def _call(operation):
    try:
        return run_browser_operation(operation)
    except BrowserError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/open")
def open_page(request: BrowserOpenRequest):
    return _call(lambda: browser.open(request.url))


@router.post("/search")
def search(request: BrowserSearchRequest):
    return _call(lambda: browser.search(request.keyword))


@router.post("/click")
def click(request: BrowserLocatorRequest):
    return _call(lambda: browser.click(request.locator))


@router.post("/type")
def type_text(request: BrowserTypeRequest):
    return _call(lambda: browser.type(request.locator, request.text))


@router.post("/screenshot")
def screenshot(request: BrowserScreenshotRequest):
    filename = os.path.basename(request.filename.strip()) or "latest.png"
    if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
        filename += ".png"
    result = _call(lambda: browser.screenshot(settings.browser_screenshots_dir / filename))
    result["filename"] = filename
    return result


@router.post("/close")
def close():
    run_browser_operation(browser.close)
    return {"message": "Browser 已关闭"}


@router.get("/status")
def status():
    return _call(browser.state)


@router.get("/links")
def links(locator: str = Query("a[href]"), limit: int = Query(100, ge=1, le=500)):
    """Read visible links through the Browser facade for adapter diagnostics."""
    return _call(lambda: browser.links(locator, limit=limit))
