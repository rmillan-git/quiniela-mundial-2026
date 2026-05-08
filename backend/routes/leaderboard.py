from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
from models import Participant, Prediction, Match

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

ROUNDS = ["group_stage", "round_of_32", "round_of_16", "qf", "sf", "final"]


@router.get("/")
def leaderboard(db: Session = Depends(get_db)):
    participants = db.query(Participant).filter_by(is_approved=True).all()
    results = []
    for p in participants:
        total = db.query(func.sum(Prediction.points)).filter_by(participant_id=p.id).scalar() or 0
        by_round = {}
        for r in ROUNDS:
            pts = (
                db.query(func.sum(Prediction.points))
                .join(Match, Prediction.match_id == Match.id)
                .filter(Prediction.participant_id == p.id, Match.round == r)
                .scalar()
                or 0
            )
            by_round[r] = pts
        results.append({"id": p.id, "name": p.name, "total": total, "by_round": by_round})

    results.sort(key=lambda x: x["total"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


@router.get("/groups")
def group_standings(db: Session = Depends(get_db)):
    """Return group table standings computed from finished group-stage matches."""
    from models import Team
    teams = db.query(Team).all()
    standings: dict[str, dict] = {}

    for t in teams:
        standings[t.name] = {
            "team": t.name, "flag": t.flag_emoji, "group": t.group,
            "played": 0, "won": 0, "drawn": 0, "lost": 0,
            "gf": 0, "ga": 0, "pts": 0,
        }

    matches = db.query(Match).filter_by(round="group_stage", is_finished=True).all()
    for m in matches:
        if not m.home_team or not m.away_team:
            continue
        h, a = m.home_team.name, m.away_team.name
        hg, ag = m.home_score, m.away_score
        standings[h]["played"] += 1
        standings[a]["played"] += 1
        standings[h]["gf"] += hg
        standings[h]["ga"] += ag
        standings[a]["gf"] += ag
        standings[a]["ga"] += hg
        if hg > ag:
            standings[h]["won"] += 1; standings[h]["pts"] += 3
            standings[a]["lost"] += 1
        elif ag > hg:
            standings[a]["won"] += 1; standings[a]["pts"] += 3
            standings[h]["lost"] += 1
        else:
            standings[h]["drawn"] += 1; standings[h]["pts"] += 1
            standings[a]["drawn"] += 1; standings[a]["pts"] += 1

    by_group: dict[str, list] = {}
    for s in standings.values():
        g = s["group"]
        by_group.setdefault(g, []).append(s)

    for g in by_group:
        by_group[g].sort(key=lambda x: (-x["pts"], -(x["gf"] - x["ga"]), -x["gf"]))

    return by_group
