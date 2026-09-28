from fastapi import APIRouter, HTTPException

from app.services.stocks import StockDataError, get_stock_history, get_stock_quotes

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/quotes")
def quotes():
    try:
        return get_stock_quotes()
    except StockDataError as exc:
        raise HTTPException(status_code=502, detail="Stock data unavailable") from exc


@router.get("/{code}/history")
def history(code: str, period: str = "6m"):
    try:
        return get_stock_history(code, period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StockDataError as exc:
        raise HTTPException(status_code=502, detail="Stock data unavailable") from exc
