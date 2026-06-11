from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Match, Participant, Prediction
from routes.auth import get_current_participant

router = APIRouter(prefix="/predictions", tags=["predictions"])


class PredictionRequest(BaseModel):
    home_score: int
    away_score: int


def _calc_points(ph: int, pa: int, rh: int, ra: int) -> int:
    def outcome(h, a): return "home" if h > a else ("away" if a > h else "draw")
    if outcome(ph, pa) != outcome(rh, ra):
        return 0
    return 5 + (2 if ph == rh else 0) + (2 if pa == ra else 0)


@router.get("/my")
def my_predictions(current=Depends(get_current_participant), db: Session = Depends(get_db)):
    preds = db.query(Prediction).filter_by(participant_id=current.id).all()
    return [
        {"match_id": p.match_id, "home_score": p.home_score, "away_score": p.away_score, "points": p.points}
        for p in preds
    ]


PREDICTIONS_REVEAL_UTC = datetime(2026, 6, 10, 5, 0, 0, tzinfo=timezone.utc)  # Jun 10 00:00 CST
PREDICTIONS_CLOSE_UTC  = datetime(2026, 6, 11, 17, 0, 0, tzinfo=timezone.utc)  # Jun 11 12:00 PM CDT


@router.get("/all")
def all_predictions(current=Depends(get_current_participant), db: Session = Depends(get_db)):
    """All participants' predictions — locked until Jun 10 (admins can always view)."""
    if not current.is_admin and datetime.now(timezone.utc) < PREDICTIONS_REVEAL_UTC:
        raise HTTPException(423, "Predictions are locked until June 10, 2026")

    participants = db.query(Participant).filter_by(is_approved=True).order_by(Participant.name).all()
    matches_q = db.query(Match).order_by(Match.match_number).all()
    preds = db.query(Prediction).join(Participant).filter(Participant.is_approved == True).all()
    pred_map = {(p.match_id, p.participant_id): p for p in preds}
    return {
        "participants": [{"id": p.id, "name": p.name} for p in participants],
        "matches": [
            {
                "id": m.id, "match_number": m.match_number, "round": m.round,
                "group": m.group,
                "home_team": m.home_team, "away_team": m.away_team,
                "home_flag": m.home_flag, "away_flag": m.away_flag,
                "home_score": m.home_score, "away_score": m.away_score,
                "is_finished": m.is_finished,
                "kickoff_utc": m.kickoff_utc.isoformat() if m.kickoff_utc else None,
            }
            for m in matches_q
        ],
        "predictions": [
            {
                "match_id": p.match_id, "participant_id": p.participant_id,
                "home_score": p.home_score, "away_score": p.away_score, "points": p.points,
            }
            for p in preds
        ],
    }


@router.put("/{match_id}")
def upsert_prediction(
    match_id: int,
    req: PredictionRequest,
    current=Depends(get_current_participant),
    db: Session = Depends(get_db),
):
    match = db.query(Match).get(match_id)
    if not match:
        raise HTTPException(404, "Match not found")
    if datetime.now(timezone.utc) >= PREDICTIONS_CLOSE_UTC:
        raise HTTPException(400, "Predictions locked — deadline has passed (June 11 12:00 PM CT)")

    pred = db.query(Prediction).filter_by(participant_id=current.id, match_id=match_id).first()
    if pred:
        pred.home_score = req.home_score
        pred.away_score = req.away_score
    else:
        pred = Prediction(
            participant_id=current.id,
            match_id=match_id,
            home_score=req.home_score,
            away_score=req.away_score,
        )
        db.add(pred)

    # Score immediately if match already has a result (e.g. after admin simulation)
    if match.is_finished and match.home_score is not None:
        pred.points = _calc_points(pred.home_score, pred.away_score, match.home_score, match.away_score)

    db.commit()
    return {"ok": True}
