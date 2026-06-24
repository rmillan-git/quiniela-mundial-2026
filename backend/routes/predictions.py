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
    predicted_winner_side: str | None = None  # "home" or "away" — knockout only, when predicting a draw


from routes.matches import _calc_points, KNOCKOUT_ROUNDS


@router.get("/my")
def my_predictions(current=Depends(get_current_participant), db: Session = Depends(get_db)):
    preds = db.query(Prediction).filter_by(participant_id=current.id).all()
    return [
        {
            "match_id": p.match_id,
            "home_score": p.home_score,
            "away_score": p.away_score,
            "points": p.points,
            "predicted_winner_side": p.predicted_winner_side,
        }
        for p in preds
    ]


PREDICTIONS_CLOSE_UTC  = datetime(2026, 6, 12, 1, 0, 0, tzinfo=timezone.utc)  # Jun 11 8:00 PM CDT


@router.get("/all")
def all_predictions(current=Depends(get_current_participant), db: Session = Depends(get_db)):
    """All participants' predictions — revealed after close time (admins can always view)."""
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
                "home_team": m.home_team.name if m.home_team else m.home_team_placeholder,
                "away_team": m.away_team.name if m.away_team else m.away_team_placeholder,
                "home_flag": m.home_team.flag_emoji if m.home_team else "🏳️",
                "away_flag": m.away_team.flag_emoji if m.away_team else "🏳️",
                "home_score": m.home_score, "away_score": m.away_score,
                "is_finished": m.is_finished,
                "kickoff_utc": m.kickoff_utc.isoformat() + "Z" if m.kickoff_utc else None,
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
    now = datetime.now(timezone.utc)
    kickoff = match.kickoff_utc if match.kickoff_utc.tzinfo else match.kickoff_utc.replace(tzinfo=timezone.utc)
    if now >= kickoff:
        raise HTTPException(400, "Predictions locked — this match has already started")

    pred = db.query(Prediction).filter_by(participant_id=current.id, match_id=match_id).first()
    if pred:
        pred.home_score = req.home_score
        pred.away_score = req.away_score
        pred.predicted_winner_side = req.predicted_winner_side
    else:
        pred = Prediction(
            participant_id=current.id,
            match_id=match_id,
            home_score=req.home_score,
            away_score=req.away_score,
            predicted_winner_side=req.predicted_winner_side,
        )
        db.add(pred)

    if match.is_finished and match.home_score is not None:
        pred.points = _calc_points(
            pred.home_score, pred.away_score, match.home_score, match.away_score,
            round_=match.round,
            pred_winner_side=pred.predicted_winner_side,
            winner_id=match.winner_id,
            home_team_id=match.home_team_id,
            away_team_id=match.away_team_id,
        )

    db.commit()
    return {"ok": True}
