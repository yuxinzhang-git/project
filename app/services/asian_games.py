"""Read-only adapter for the official Aichi-Nagoya 2026 results service."""

from __future__ import annotations

import gzip
import json
import zlib
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

from app.services.asian_games_localization import localize_discipline, localize_text, localize_venue


ASIAN_GAMES_SOURCE = "https://back.results.asiangames2026.org"
ASIAN_GAMES_PAGE = "https://results.asiangames2026.org/"
SHANGHAI = timezone(timedelta(hours=8), name="Asia/Shanghai")
REQUEST_TIMEOUT_SECONDS = 20.0
REQUEST_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": ASIAN_GAMES_PAGE.rstrip("/"),
    "Referer": ASIAN_GAMES_PAGE,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36",
}


def _value(record: dict[str, Any], *names: str, default: Any = "") -> Any:
    for name in names:
        value = record.get(name)
        if value not in (None, "", [], {}):
            return value
    return default


def _flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    """Make Bornan's nested Info/Unit records readable without losing outer data."""
    flattened: dict[str, Any] = {}
    for key in ("Event", "Unit", "Info", "Competition", "Match"):
        nested = record.get(key)
        if isinstance(nested, dict):
            flattened.update(nested)
    flattened.update(record)
    return flattened


def _parse_datetime(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(value / 1000 if value > 10_000_000_000 else value, timezone.utc)
    else:
        text = str(value).strip()
        if not text:
            return ""
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(SHANGHAI).isoformat(timespec="seconds")


def _participants(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, str):
            result.append({"name": item})
        elif isinstance(item, dict):
            name = _value(item, "name", "Name", "displayName", "DisplayName", "shortName", "ShortName")
            result.append({"name": name, **item})
    return result


def _status(record: dict[str, Any], start_time: str) -> str:
    raw = str(_value(record, "status", "Status", "state", "State", "phase", "Phase")).lower()
    if raw in {"live", "in", "ongoing", "running", "started", "live_now", "getting_ready", "1"} or record.get("IsLive") is True:
        return "live"
    if raw in {"finished", "finish", "final", "completed", "complete", "post", "ended", "official", "unofficial", "f", "2"} or record.get("IsFinished") is True:
        return "finished"
    return "upcoming"


def normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    record = _flatten_record(raw)
    start_time = _parse_datetime(_value(record, "start_time", "StartTime", "startDate", "StartDate", "dateTime", "DateTime", "scheduledStart", "ScheduledStart", "DateTimeRaw", "date", "Date"))
    status = _status(record, start_time)
    discipline = _value(record, "discipline", "Discipline", "disciplineName", "DisciplineName", "DiscDesc", "Disc", default="")
    sport = _value(record, "sport", "Sport", "sportName", "SportName", "SportDesc", default="")
    venue = _value(record, "venueName", "VenueName", "VenueDesc", "VenueDescS", "LocDesc", "venue", "Venue", default="")
    for field_name, field_value in (("discipline", discipline), ("sport", sport), ("venue", venue)):
        if isinstance(field_value, dict):
            record[field_name] = _value(field_value, "name", "Name", "displayName", "DisplayName")
    title = _value(record, "title", "Title", "eventName", "EventName", "name", "Name", "description", "Description", "UnitDesc", "UnitDescS", "PhaseDesc", "EventDesc", "Event", default="")
    identifier = _value(record, "id", "Id", "ID", "unitId", "UnitId", "eventId", "EventId", "Key", "ResCode", default="")
    score = _value(record, "score", "Score", "scores", "Scores", "results", "Results", default={})
    if score in (None, "", {}, []):
        score = {}
        for side_name, side_key in (("home", "Home"), ("away", "Away")):
            side = record.get(side_key)
            if isinstance(side, dict):
                result = _value(side, "result", "Result", default="")
                name = _value(side, "name", "Name", default=side_name)
                if result not in (None, ""):
                    score[str(name)] = result
    if not isinstance(score, dict):
        score = {"value": score} if score not in ("", None) else {}
    participants = _value(record, "participants", "Participants", "competitors", "Competitors", "teams", "Teams")
    if not isinstance(participants, list):
        participants = [record[key] for key in ("Home", "Away") if isinstance(record.get(key), dict)]
    return {
        "id": str(identifier),
        "sport": localize_text(record.get("sport", sport) or ""),
        "discipline": localize_discipline(record.get("discipline", discipline) or ""),
        "title": localize_text(title or record.get("discipline", discipline) or "未命名赛事"),
        "start_time": start_time,
        "status": status,
        "venue": localize_venue(record.get("venue", venue) or ""),
        "participants": _participants(participants),
        "score": score,
        "source_url": ASIAN_GAMES_PAGE,
    }


def _looks_like_event(value: dict[str, Any]) -> bool:
    keys = {key.lower() for key in value}
    has_identifier = bool(keys & {"id", "unitid", "eventid", "key", "rescode"})
    has_event_field = bool(keys & {"title", "eventname", "name", "starttime", "startdate", "datetime", "datetimeraw", "scheduledstart", "competitors", "participants", "status", "islive", "discdesc", "eventdesc", "phasedesc", "unitdesc"})
    return has_identifier and has_event_field


def _find_events(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if _looks_like_event(value):
            found.append(value)
        for nested in value.values():
            found.extend(_find_events(nested))
    elif isinstance(value, list):
        for nested in value:
            found.extend(_find_events(nested))
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in found:
        key = str(_value(item, "id", "Id", "ID", "unitId", "UnitId", "eventId", "EventId", "Key", "ResCode", default=id(item)))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def decode_bornan_payload(raw: bytes) -> Any:
    """Decode JSON, standard compression, and Bornan's UTF-8-wrapped zlib body."""
    candidates = [raw]
    try:
        candidates.append(raw.decode("utf-8").encode("latin1"))
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    decoded: list[bytes] = []
    for candidate in candidates:
        decoded.append(candidate)
    for wbits in (zlib.MAX_WBITS, zlib.MAX_WBITS | 16, -zlib.MAX_WBITS):
            try:
                decoded.append(zlib.decompress(candidate, wbits))
            except zlib.error:
                continue
    for candidate in decoded:
        try:
            return json.loads(candidate.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise ValueError("Asian Games provider returned an unreadable payload")


def _request_payload(date_text: str) -> Any:
    url = f"{ASIAN_GAMES_SOURCE}/s/AG2026/en/ALL/schedule/day/{quote(date_text)}"
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=False) as client:
            response = client.get(url, headers=REQUEST_HEADERS)
            response.raise_for_status()
            return decode_bornan_payload(response.content)
    except (httpx.HTTPError, OSError, ValueError) as exc:
        raise RuntimeError(f"Asian Games provider unavailable: {exc}") from exc


def asian_games_feed(date_text: str | None = None) -> dict[str, Any]:
    query_date = date_text or datetime.now(SHANGHAI).date().isoformat()
    try:
        date.fromisoformat(query_date)
    except (TypeError, ValueError) as exc:
        raise ValueError("日期必须为 YYYY-MM-DD") from exc
    if len(query_date) != 10:
        raise ValueError("日期必须为 YYYY-MM-DD")

    payload = _request_payload(query_date)
    events = [normalize_event(item) for item in _find_events(payload)]
    groups = {"finished": [], "live": [], "upcoming": []}
    for event in events:
        groups[event["status"]].append(event)
    for group in groups.values():
        group.sort(key=lambda item: item["start_time"] or "9999")
    return {
        "event": "2026年亚运会",
        "date": query_date,
        "timezone": "Asia/Shanghai",
        "updated_at": datetime.now(SHANGHAI).isoformat(timespec="seconds"),
        "source": ASIAN_GAMES_PAGE,
        "source_status": "live",
        **groups,
        "total": len(events),
    }
