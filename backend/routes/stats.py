import time
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, settings
from models import Team

router = APIRouter(prefix="/stats", tags=["stats"])

_cache: dict = {"data": None, "ts": 0.0}
_CACHE_TTL = 300  # 5 minutes


def _flag_map(db: Session) -> dict[str, str]:
    """team name (lower) → flag emoji from our DB."""
    return {t.name.lower(): t.flag_emoji for t in db.query(Team).all()}


@router.get("/")
def get_tournament_stats(db: Session = Depends(get_db)):
    if time.time() - _cache["ts"] < _CACHE_TTL and _cache["data"] is not None:
        return _cache["data"]

    api_key = settings.football_data_api_key
    if not api_key:
        raise HTTPException(503, "FOOTBALL_DATA_API_KEY not configured")

    headers = {"X-Auth-Token": api_key}
    flags = _flag_map(db)

    def team_flag(name: str) -> str:
        return flags.get(name.lower(), "🏳️")

    # ── Top scorers ──────────────────────────────────────────────────────────
    scorers: list[dict] = []
    try:
        r = httpx.get(
            "https://api.football-data.org/v4/competitions/WC/scorers",
            headers=headers,
            params={"limit": 30},
            timeout=15,
        )
        r.raise_for_status()
        for s in r.json().get("scorers", []):
            team_name = (s.get("team") or {}).get("name", "")
            scorers.append({
                "player":    (s.get("player") or {}).get("name", ""),
                "team":      team_name,
                "flag":      team_flag(team_name),
                "goals":     s.get("goals") or 0,
                "assists":   s.get("assists") or 0,
                "penalties": s.get("penalties") or 0,
            })
    except Exception as e:
        print(f"stats scorers error: {e}")

    # ── Cards + assists from match events ────────────────────────────────────
    cards_by_team: dict[str, dict] = {}
    assists_by_player: dict[str, dict] = {}

    try:
        r = httpx.get(
            "https://api.football-data.org/v4/competitions/WC/matches",
            headers=headers,
            params={"status": "FINISHED"},
            timeout=15,
        )
        r.raise_for_status()
        for m in r.json().get("matches", []):
            # Cards
            for bk in m.get("bookings", []):
                t = (bk.get("team") or {}).get("name", "")
                if not t:
                    continue
                if t not in cards_by_team:
                    cards_by_team[t] = {"team": t, "flag": team_flag(t), "yellow": 0, "red": 0}
                card = bk.get("card", "")
                if "YELLOW_RED" in card or "SECOND_YELLOW" in card:
                    cards_by_team[t]["yellow"] += 1
                    cards_by_team[t]["red"] += 1
                elif "YELLOW" in card:
                    cards_by_team[t]["yellow"] += 1
                elif "RED" in card:
                    cards_by_team[t]["red"] += 1

            # Assists from goal events (supplement scorers endpoint)
            for g in m.get("goals", []):
                assist = g.get("assist")
                if not assist:
                    continue
                pname = assist.get("name", "")
                if not pname:
                    continue
                t = (g.get("team") or {}).get("name", "")
                if pname not in assists_by_player:
                    assists_by_player[pname] = {"player": pname, "team": t, "flag": team_flag(t), "assists": 0}
                assists_by_player[pname]["assists"] += 1
    except Exception as e:
        print(f"stats cards/assists error: {e}")

    cards = sorted(cards_by_team.values(), key=lambda x: -(x["yellow"] + x["red"] * 2))

    # Merge match-derived assists into scorers list (API scorers may be incomplete)
    scorer_names = {s["player"] for s in scorers}
    extra_assisters = [
        v for v in assists_by_player.values()
        if v["player"] not in scorer_names and v["assists"] > 0
    ]
    top_assisters = sorted(
        [{"player": s["player"], "team": s["team"], "flag": s["flag"], "assists": s["assists"]}
         for s in scorers if s["assists"] > 0] + extra_assisters,
        key=lambda x: -x["assists"],
    )

    result = {"scorers": scorers, "cards": cards, "top_assisters": top_assisters}
    _cache["data"] = result
    _cache["ts"] = time.time()
    return result
