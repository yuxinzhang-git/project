from datetime import date as current_date

import time

import httpx

def _get_json(url: str, params: dict) -> httpx.Response:
    last_error = None
    for attempt in range(2):
        try:
            with httpx.Client(timeout=12, follow_redirects=True, trust_env=False, http2=False) as client:
                response = client.get(url, params=params, headers={'User-Agent': 'my-agent/2.0'})
            response.raise_for_status()
            return response
        except (httpx.HTTPError, OSError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.4)
    raise RuntimeError(f'sports provider unavailable: {last_error}') from last_error

def _team(competitor: dict) -> dict:
    team = competitor.get("team", {})
    return {"name": team.get("displayName", "Unknown"), "abbreviation": team.get("abbreviation", ""), "logo": team.get("logo", ""), "score": competitor.get("score", "-"), "record": (competitor.get("records") or [{}])[0].get("summary", "")}


def nba_scoreboard() -> dict:
    return sports_feed("nba", None)


def sports_feed(league: str, date: str | None) -> dict:
    configs = {"nba": ("basketball", "nba", "NBA"), "worldcup": ("soccer", "fifa.world", "World Cup")}
    if league not in configs:
        raise ValueError("Unsupported sports league")
    sport, competition, label = configs[league]
    query_date = date or current_date.today().isoformat()
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{competition}/scoreboard"
    response = _get_json(url, {"dates": query_date.replace("-", "")})
    payload = response.json()
    games = []
    for event in payload.get("events", []):
        item = event.get("competitions", [{}])[0]
        competitors = item.get("competitors", [])
        home = next((entry for entry in competitors if entry.get("homeAway") == "home"), competitors[0] if competitors else {})
        away = next((entry for entry in competitors if entry.get("homeAway") == "away"), competitors[1] if len(competitors) > 1 else {})
        status = item.get("status", {}).get("type", {})
        games.append({"id": event.get("id"), "date": event.get("date"), "status": status.get("description", status.get("detail", "")), "state": status.get("state", "pre"), "clock": item.get("status", {}).get("displayClock", ""), "home_team": _team(home), "away_team": _team(away), "venue": item.get("venue", {}).get("fullName", "")})
    return {"league": label, "date": query_date, "total_games": len(games), "games": games}


def sports_game(league: str, event_id: str) -> dict:
    configs = {"nba": ("basketball", "nba"), "worldcup": ("soccer", "fifa.world")}
    if league not in configs:
        raise ValueError("Unsupported sports league")
    sport, competition = configs[league]
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{competition}/summary"
    response = _get_json(url, {"event": event_id})
    payload = response.json()
    competition_data = payload.get("header", {}).get("competitions", [{}])[0]
    players = []
    for side in payload.get("boxscore", {}).get("players", []):
        statistics = side.get("statistics", [])
        labels = statistics[0].get("names", []) if statistics else []
        for athlete in side.get("statistics", [{}])[0].get("athletes", []):
            players.append({"name": athlete.get("athlete", {}).get("displayName", ""), "team": side.get("team", {}).get("abbreviation", ""), "stats": dict(zip(labels, athlete.get("statistics", [])))})
    return {"id": event_id, "competition": competition_data, "players": players}

