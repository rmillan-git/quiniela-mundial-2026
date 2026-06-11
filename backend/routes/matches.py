from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
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
        "kickoff_utc": m.kickoff_utc.isoformat() if m.kickoff_utc else None,
        "venue": m.venue,
        "home_score": m.home_score,
        "away_score": m.away_score,
        "is_finished": m.is_finished,
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


@router.patch("/{mid}/result")
def set_result(mid: int, req: ResultRequest, db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    m = db.query(Match).get(mid)
    if not m:
        raise HTTPException(404, "Match not found")
    m.home_score = req.home_score
    m.away_score = req.away_score
    m.is_finished = True
    for pred in m.predictions:
        pred.points = _calc_points(pred.home_score, pred.away_score, req.home_score, req.away_score)
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
            pred.points = _calc_points(pred.home_score, pred.away_score, m.home_score, m.away_score)
            total += 1
    db.commit()
    return {"rescored": total}


def _outcome(h: int, a: int) -> str:
    if h > a: return "home"
    if a > h: return "away"
    return "draw"


def _calc_points(ph: int, pa: int, rh: int, ra: int) -> int:
    if _outcome(ph, pa) != _outcome(rh, ra):
        return 0
    return 5 + (2 if ph == rh else 0) + (2 if pa == ra else 0)
