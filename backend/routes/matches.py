import re as _re
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx
from database import get_db, settings
from models import Match, Team, Participant
from routes.auth import get_current_admin

router = APIRouter(prefix="/matches", tags=["matches"])


def match_to_dict(m: Match) -> dict:
    return {
        "id": m.id,
        "match_number": m.match_number,
        "round": m.round,
        "group": m.group,
        "home_team": m.home_team.name if m.home_team else m.home_team_placeholder,
        "away_team": m.away_team.name if m.away_team else m.away_team_placeholder,
        "home_flag": m.home_team.flag_emoji if m.home_team else "🏳️",
        "away_flag": m.away_team.flag_emoji if m.away_team else "🏳️",
        "home_team_id": m.home_team_id,
        "away_team_id": m.away_team_id,
        "kickoff_utc": m.kickoff_utc.isoformat() + "Z" if m.kickoff_utc else None,
        "venue": m.venue,
        "home_score": m.home_score,
        "away_score": m.away_score,
        "is_finished": m.is_finished,
        "winner_id": m.winner_id,
        "winner_name": m.winner.name if m.winner else None,
        "winner_flag": m.winner.flag_emoji if m.winner else None,
        "home_team_placeholder": m.home_team_placeholder,
        "away_team_placeholder": m.away_team_placeholder,
    }


@router.get("/")
def list_matches(round: str | None = None, group: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Match)
    if round:
        q = q.filter(Match.round == round)
    if group:
        q = q.filter(Match.group == group)
    return [match_to_dict(m) for m in q.order_by(Match.match_number).all()]


@router.get("/{mid}")
def get_match(mid: int, db: Session = Depends(get_db)):
    m = db.query(Match).get(mid)
    if not m:
        raise HTTPException(404, "Match not found")
    return match_to_dict(m)


class ResultRequest(BaseModel):
    home_score: int
    away_score: int
    winner_id: int | None = None  # team ID that advances — only for knockout draws (penalties)


@router.patch("/{mid}/result")
def set_result(mid: int, req: ResultRequest, db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    m = db.query(Match).get(mid)
    if not m:
        raise HTTPException(404, "Match not found")
    m.home_score = req.home_score
    m.away_score = req.away_score
    m.is_finished = True
    if req.winner_id is not None:
        m.winner_id = req.winner_id
    for pred in m.predictions:
        pred.points = _calc_points(
            pred.home_score, pred.away_score, req.home_score, req.away_score,
            round_=m.round,
            pred_winner_side=getattr(pred, "predicted_winner_side", None),
            winner_id=req.winner_id or m.winner_id,
            home_team_id=m.home_team_id,
            away_team_id=m.away_team_id,
        )
    db.commit()
    return match_to_dict(m)


class TeamAssignRequest(BaseModel):
    home_team_id: int | None = None
    away_team_id: int | None = None


@router.patch("/{mid}/teams")
def assign_teams(mid: int, req: TeamAssignRequest, db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    """Set real teams on a knockout match once group stage results are known."""
    m = db.query(Match).get(mid)
    if not m:
        raise HTTPException(404, "Match not found")
    if req.home_team_id is not None:
        if not db.query(Team).get(req.home_team_id):
            raise HTTPException(404, "Home team not found")
        m.home_team_id = req.home_team_id
    if req.away_team_id is not None:
        if not db.query(Team).get(req.away_team_id):
            raise HTTPException(404, "Away team not found")
        m.away_team_id = req.away_team_id
    db.commit()
    return match_to_dict(m)


@router.patch("/{mid}/reset")
def reset_result(mid: int, db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    m = db.query(Match).get(mid)
    if not m:
        raise HTTPException(404, "Match not found")
    m.home_score = None
    m.away_score = None
    m.is_finished = False
    for pred in m.predictions:
        pred.points = None
    db.commit()
    return match_to_dict(m)


@router.post("/recalculate")
def recalculate_all(db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    """Re-score all predictions for every finished match."""
    matches = db.query(Match).filter(Match.is_finished == True).all()
    total = 0
    for m in matches:
        for pred in m.predictions:
            pred.points = _calc_points(
                pred.home_score, pred.away_score, m.home_score, m.away_score,
                round_=m.round,
                pred_winner_side=getattr(pred, "predicted_winner_side", None),
                winner_id=m.winner_id,
                home_team_id=m.home_team_id,
                away_team_id=m.away_team_id,
            )
            total += 1
    db.commit()
    return {"rescored": total}


KNOCKOUT_ROUNDS = {"round_of_32", "round_of_16", "qf", "sf", "final"}


def _outcome(h: int, a: int) -> str:
    if h > a: return "home"
    if a > h: return "away"
    return "draw"


def _calc_points(
    ph: int, pa: int, rh: int, ra: int,
    round_: str = "group_stage",
    pred_winner_side: str | None = None,
    winner_id: int | None = None,
    home_team_id: int | None = None,
    away_team_id: int | None = None,
) -> int:
    if round_ in KNOCKOUT_ROUNDS:
        # Determine actual winner side
        if rh > ra:
            actual_side = "home"
        elif ra > rh:
            actual_side = "away"
        else:
            if winner_id is None:
                return 0  # penalty winner not set yet
            actual_side = "home" if winner_id == home_team_id else "away"
        # Determine predicted winner side
        if ph > pa:
            pred_side = "home"
        elif pa > ph:
            pred_side = "away"
        else:
            pred_side = pred_winner_side  # None if participant didn't pick penalty winner
        if not pred_side or pred_side != actual_side:
            return 0
        return 5 + (2 if ph == rh else 0) + (2 if pa == ra else 0)
    else:
        if _outcome(ph, pa) != _outcome(rh, ra):
            return 0
        return 5 + (2 if ph == rh else 0) + (2 if pa == ra else 0)


def _name_matches(api_name: str, db_name: str) -> bool:
    """Loose team name comparison to handle minor differences between sources."""
    a, b = api_name.lower().strip(), db_name.lower().strip()
    return a == b or a in b or b in a


def sync_results_from_api(db: Session) -> dict:
    """Fetch finished World Cup 2026 matches from football-data.org and update DB."""
    api_key = settings.football_data_api_key
    if not api_key:
        return {"error": "FOOTBALL_DATA_API_KEY not set", "updated": 0}

    resp = httpx.get(
        "https://api.football-data.org/v4/competitions/WC/matches",
        headers={"X-Auth-Token": api_key},
        params={"status": "FINISHED"},
        timeout=15,
    )
    resp.raise_for_status()
    matches_data = resp.json().get("matches", [])

    updated = 0
    for m_api in matches_data:
        score = m_api.get("score", {}).get("fullTime", {})
        home_score = score.get("home")
        away_score = score.get("away")
        if home_score is None or away_score is None:
            continue

        # Match by kickoff UTC time (strip timezone for comparison with naive DB datetimes)
        utc_date = datetime.fromisoformat(m_api["utcDate"].replace("Z", "+00:00"))
        naive_utc = utc_date.replace(tzinfo=None)

        api_home = m_api.get("homeTeam", {}).get("name", "")
        api_away = m_api.get("awayTeam", {}).get("name", "")

        candidates = db.query(Match).filter(Match.kickoff_utc == naive_utc).all()

        # Fallback: if no exact time match, try ±15 min window with team name verification
        # (handles cases where API returns actual kickoff time instead of scheduled time)
        if not candidates and api_home and api_away:
            window_start = naive_utc - timedelta(minutes=15)
            window_end = naive_utc + timedelta(minutes=15)
            nearby = db.query(Match).filter(
                Match.kickoff_utc >= window_start,
                Match.kickoff_utc <= window_end,
            ).all()
            for c in nearby:
                if c.home_team and c.away_team:
                    if _name_matches(api_home, c.home_team.name) and _name_matches(api_away, c.away_team.name):
                        candidates = [c]
                        break

        if not candidates:
            continue

        db_match = None
        if len(candidates) == 1:
            db_match = candidates[0]
        else:
            # Multiple matches at same kickoff time — disambiguate by team name
            for c in candidates:
                if c.home_team and c.away_team:
                    if _name_matches(api_home, c.home_team.name) and _name_matches(api_away, c.away_team.name):
                        db_match = c
                        break
            if not db_match:
                db_match = candidates[0]  # fallback

        if db_match.is_finished and db_match.home_score == home_score and db_match.away_score == away_score:
            continue  # already up to date

        db_match.home_score = home_score
        db_match.away_score = away_score
        db_match.is_finished = True
        for pred in db_match.predictions:
            pred.points = _calc_points(
                pred.home_score, pred.away_score, home_score, away_score,
                round_=db_match.round,
                pred_winner_side=getattr(pred, "predicted_winner_side", None),
                winner_id=db_match.winner_id,
                home_team_id=db_match.home_team_id,
                away_team_id=db_match.away_team_id,
            )
        updated += 1

    db.commit()
    return {"updated": updated, "total_finished": len(matches_data)}


@router.post("/sync")
def sync_results(db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    """Manually trigger a sync of World Cup results from football-data.org."""
    result = sync_results_from_api(db)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


def _build_group_standings(db: Session) -> dict:
    """Returns {group: [(team_id, pts, gd, gf), ...]} sorted by standings."""
    group_matches = db.query(Match).filter(Match.round == "group_stage").all()

    team_stats: dict[str, dict[int, dict]] = {}
    for m in group_matches:
        g = m.group
        if not g:
            continue
        if g not in team_stats:
            team_stats[g] = {}
        for tid in filter(None, [m.home_team_id, m.away_team_id]):
            if tid not in team_stats[g]:
                team_stats[g][tid] = {"pts": 0, "gd": 0, "gf": 0}
        if not m.is_finished or m.home_score is None or not m.home_team_id or not m.away_team_id:
            continue
        h, a = m.home_score, m.away_score
        team_stats[g][m.home_team_id]["gf"] += h
        team_stats[g][m.home_team_id]["gd"] += h - a
        team_stats[g][m.away_team_id]["gf"] += a
        team_stats[g][m.away_team_id]["gd"] += a - h
        if h > a:
            team_stats[g][m.home_team_id]["pts"] += 3
        elif h == a:
            team_stats[g][m.home_team_id]["pts"] += 1
            team_stats[g][m.away_team_id]["pts"] += 1
        else:
            team_stats[g][m.away_team_id]["pts"] += 3

    result = {}
    for g, stats in team_stats.items():
        result[g] = sorted(
            ((tid, s["pts"], s["gd"], s["gf"]) for tid, s in stats.items()),
            key=lambda x: (-x[1], -x[2], -x[3]),
        )
    return result


@router.post("/assign-ko-from-standings")
def assign_ko_from_standings(db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    """Tentatively assign group-stage leaders to Round of 32 slots from current standings."""
    standings = _build_group_standings(db)

    # Rank all 3rd-place teams globally for "Mejor 3°" slots
    all_thirds: list[tuple] = []
    for g, ranked in standings.items():
        if len(ranked) >= 3:
            tid, pts, gd, gf = ranked[2]
            all_thirds.append((pts, gd, gf, g, tid))
    all_thirds.sort(key=lambda x: (-x[0], -x[1], -x[2]))
    # Top 8 qualify; map group → (team_id, global_rank)
    third_by_group: dict[str, tuple] = {
        g: (tid, i) for i, (_, _, _, g, tid) in enumerate(all_thirds[:8])
    }

    used_third_groups: set[str] = set()

    def resolve(placeholder: str) -> int | None:
        if not placeholder:
            return None
        ph = placeholder.strip()

        # "1° Grupo A" / "2° Grupo B"
        m1 = _re.match(r"^(\d+)\D+Grupo\s+([A-L])$", ph)
        if m1:
            pos = int(m1.group(1)) - 1
            g = m1.group(2)
            ranked = standings.get(g, [])
            return ranked[pos][0] if len(ranked) > pos else None

        # "Mejor 3° (A/B/C/D/F)"
        m2 = _re.match(r"Mejor\s+3\D*\(([A-L/]+)\)", ph)
        if m2:
            candidate_groups = [x.strip() for x in m2.group(1).split("/")]
            best_rank, best_tid = 999, None
            best_g = None
            for cg in candidate_groups:
                if cg in third_by_group and cg not in used_third_groups:
                    _, rank = third_by_group[cg]
                    if rank < best_rank:
                        best_rank, best_tid, best_g = rank, third_by_group[cg][0], cg
            if best_g:
                used_third_groups.add(best_g)
                return best_tid

        return None

    ko_matches = db.query(Match).filter(Match.round == "round_of_32").order_by(Match.match_number).all()

    assigned = 0
    details = []
    for m in ko_matches:
        if m.is_finished:
            continue
        new_home = resolve(m.home_team_placeholder)
        new_away = resolve(m.away_team_placeholder)
        changed = False
        if new_home is not None and m.home_team_id != new_home:
            m.home_team_id = new_home
            changed = True
        if new_away is not None and m.away_team_id != new_away:
            m.away_team_id = new_away
            changed = True
        if changed:
            assigned += 1
        home_team = db.query(Team).get(m.home_team_id) if m.home_team_id else None
        away_team = db.query(Team).get(m.away_team_id) if m.away_team_id else None
        details.append({
            "match_number": m.match_number,
            "home_placeholder": m.home_team_placeholder,
            "away_placeholder": m.away_team_placeholder,
            "home_team": home_team.name if home_team else None,
            "home_flag": home_team.flag_emoji if home_team else None,
            "away_team": away_team.name if away_team else None,
            "away_flag": away_team.flag_emoji if away_team else None,
        })

    db.commit()
    return {"assigned": assigned, "matches": details}
