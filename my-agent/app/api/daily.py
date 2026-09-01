from fastapi import APIRouter, HTTPException

from app.config import settings
from app.services.billing import get_billing
from app.services.sports import nba_scoreboard, sports_feed, sports_game
from app.services.weather import get_weather

router = APIRouter(prefix="/api", tags=["daily"])


@router.get("/weather")
def weather(city: str):
    try:
        return get_weather(city)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Weather unavailable: {exc}") from exc


@router.get("/sports/nba")
def nba():
    try:
        return nba_scoreboard()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sports data unavailable: {exc}") from exc


@router.get("/sports/feed/{league}")
def feed(league: str, date: str | None = None):
    try:
        return sports_feed(league, date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sports data unavailable: {exc}") from exc


@router.get("/sports/game/{league}/{event_id}")
def game(league: str, event_id: str):
    try:
        return sports_game(league, event_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Match data unavailable: {exc}") from exc


@router.get("/billing")
def billing():
    import os
    return get_billing(os.getenv("DEEPSEEK_API_KEY", ""))

