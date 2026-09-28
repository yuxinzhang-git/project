from fastapi import APIRouter, HTTPException

from app.api.web import browser, run_browser_operation
from app.browser import BrowserError
from app.browser.sites.taobao.errors import TaobaoError
from app.browser.sites.xianyu.errors import XianyuError
from app.schemas.smart import SmartOperationRequest
from app.schemas.xianyu_estimate import XianyuEstimateRequest
from app.services.smart_operation import SmartOperationError, SmartOperationService

router = APIRouter(prefix="/api/smart", tags=["smart-operation"])
service = SmartOperationService(browser)


@router.get("/capabilities")
def capabilities():
    return {"bilibili": service.bilibili.capability(), "taobao": service.taobao.capability(), "xianyu": service.xianyu.capability()}


@router.post("/xianyu/estimate")
def estimate_xianyu(request: XianyuEstimateRequest):
    try:
        return run_browser_operation(lambda: service.estimate_xianyu(request.keyword))
    except SmartOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TaobaoError as exc:
        raise HTTPException(status_code=502, detail=f"Taobao operation error ({type(exc).__name__}): {exc}") from exc
    except XianyuError as exc:
        raise HTTPException(status_code=502, detail=f"Xianyu operation error ({type(exc).__name__}): {exc}") from exc
    except BrowserError as exc:
        raise HTTPException(status_code=502, detail=f"Browser/Playwright configuration or network error: {exc}") from exc


@router.post("/execute")
def execute(request: SmartOperationRequest):
    try:
        return run_browser_operation(lambda: service.execute(request.command))
    except SmartOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TaobaoError as exc:
        raise HTTPException(status_code=502, detail=f"Taobao operation error ({type(exc).__name__}): {exc}") from exc
    except XianyuError as exc:
        raise HTTPException(status_code=502, detail=f"Xianyu operation error ({type(exc).__name__}): {exc}") from exc
    except BrowserError as exc:
        raise HTTPException(status_code=502, detail=f"Browser/Playwright configuration or network error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"智能操作失败: {exc}") from exc
