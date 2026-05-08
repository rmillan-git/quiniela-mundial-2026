from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Participant, Prediction
from routes.auth import get_current_admin

router = APIRouter(prefix="/participants", tags=["participants"])

ROUND_ORDER = ["group_stage", "round_of_32", "round_of_16", "qf", "sf", "final"]


@router.get("/")
def list_participants(db: Session = Depends(get_db)):
    return [
        {"id": p.id, "name": p.name, "email": p.email, "is_approved": p.is_approved, "registered_at": p.registered_at}
        for p in db.query(Participant).order_by(Participant.registered_at).all()
    ]


@router.get("/{pid}/predictions")
def get_participant_predictions(pid: int, db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    p = db.query(Participant).get(pid)
    if not p:
        raise HTTPException(404, "Participant not found")
    preds = db.query(Prediction).filter_by(participant_id=pid).all()
    by_round = {}
    for pred in preds:
        m = pred.match
        r = m.round
        by_round.setdefault(r, []).append({
            "match_number": m.match_number,
            "group": m.group,
            "home_team": m.home_team.name if m.home_team else m.home_team_placeholder,
            "away_team": m.away_team.name if m.away_team else m.away_team_placeholder,
            "home_flag": m.home_team.flag_emoji if m.home_team else "🏳️",
            "away_flag": m.away_team.flag_emoji if m.away_team else "🏳️",
            "kickoff_utc": m.kickoff_utc.isoformat() if m.kickoff_utc else None,
            "pred_home": pred.home_score,
            "pred_away": pred.away_score,
            "actual_home": m.home_score,
            "actual_away": m.away_score,
            "points": pred.points,
            "is_finished": m.is_finished,
        })
    # Sort each round by match_number
    for r in by_round:
        by_round[r].sort(key=lambda x: x["match_number"])
    return {
        "participant": {"id": p.id, "name": p.name, "email": p.email},
        "by_round": {r: by_round.get(r, []) for r in ROUND_ORDER if r in by_round},
        "total": sum(pred.points or 0 for pred in preds),
        "predicted": len(preds),
    }


@router.patch("/{pid}/approve")
def approve(pid: int, db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    p = db.query(Participant).get(pid)
    if not p:
        raise HTTPException(404, "Participant not found")
    p.is_approved = True
    db.commit()
    return {"ok": True}


@router.delete("/{pid}")
def delete_participant(pid: int, db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    p = db.query(Participant).get(pid)
    if not p:
        raise HTTPException(404, "Participant not found")
    if p.is_admin:
        raise HTTPException(400, "Cannot delete admin")
    db.delete(p)
    db.commit()
    return {"ok": True}
