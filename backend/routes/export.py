import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from database import get_db
from models import Match, Participant, Prediction
from routes.auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])

ROUND_LABELS = {
    "group_stage": "Group Stage",
    "round_of_32": "Round of 32",
    "round_of_16": "Round of 16",
    "qf": "Quarterfinals",
    "sf": "Semifinals",
    "final": "Final",
}
ROUND_ORDER = ["group_stage", "round_of_32", "round_of_16", "qf", "sf", "final"]

# Colors
HDR_FILL   = PatternFill("solid", fgColor="1F4E79")   # dark blue — section headers
MATCH_FILL = PatternFill("solid", fgColor="D6E4F0")   # light blue — match rows
RESULT_FILL= PatternFill("solid", fgColor="E2EFDA")   # light green — actual result
PTS_FILL   = PatternFill("solid", fgColor="FFF2CC")   # yellow — points
EXACT_FILL = PatternFill("solid", fgColor="C6EFCE")   # green — exact (9 pts)
WINNER_FILL= PatternFill("solid", fgColor="DDEBF7")   # blue — correct winner (7 pts)
WRONG_FILL = PatternFill("solid", fgColor="FCE4D6")   # red — wrong (0 pts)
WHITE_FONT = Font(color="FFFFFF", bold=True)
BOLD       = Font(bold=True)
thin = Side(style="thin")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)


def _cell(ws, row, col, value, fill=None, font=None, align="center", border=True):
    c = ws.cell(row=row, column=col, value=value)
    if fill:  c.fill = fill
    if font:  c.font = font
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    if border: c.border = BORDER
    return c


def build_excel(db: Session) -> bytes:
    wb = Workbook()

    # ── Sheet 1: Predictions grid ────────────────────────────────────────────
    ws = wb.active
    ws.title = "Predictions"

    participants = (
        db.query(Participant)
        .filter_by(is_approved=True, is_admin=False)
        .order_by(Participant.name)
        .all()
    )
    matches = db.query(Match).order_by(Match.match_number).all()
    preds = db.query(Prediction).all()

    # pred_map: (match_id, participant_id) → Prediction
    pred_map = {(p.match_id, p.participant_id): p for p in preds}

    # Column layout: A=Match#, B=Round, C=Home, D=Away, E=Result,
    #                then for each participant: Pred | Pts
    FIXED = 5
    p_cols = {}  # participant_id → (pred_col, pts_col)
    for i, p in enumerate(participants):
        p_cols[p.id] = (FIXED + 1 + i * 2, FIXED + 2 + i * 2)

    total_cols = FIXED + len(participants) * 2

    # ── Row 1: Title ──────────────────────────────────────────────────────────
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
    t = ws.cell(1, 1, "⚽ Quiniela Mundial 2026 — Predictions Export")
    t.fill = PatternFill("solid", fgColor="1F4E79")
    t.font = Font(color="FFFFFF", bold=True, size=14)
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # ── Row 2: Column headers ─────────────────────────────────────────────────
    for col, label in [(1,"#"),(2,"Round"),(3,"Home"),(4,"Away"),(5,"Result")]:
        _cell(ws, 2, col, label, fill=PatternFill("solid", fgColor="2E75B6"), font=WHITE_FONT)
    for p in participants:
        pc, ptsc = p_cols[p.id]
        ws.merge_cells(start_row=2, start_column=pc, end_row=2, end_column=ptsc)
        _cell(ws, 2, pc, p.name, fill=PatternFill("solid", fgColor="2E75B6"), font=WHITE_FONT)
        _cell(ws, 2, ptsc, "")
    ws.row_dimensions[2].height = 35

    # ── Sub-header: Pred / Pts ────────────────────────────────────────────────
    for col in range(1, FIXED+1):
        _cell(ws, 3, col, "", fill=PatternFill("solid", fgColor="BDD7EE"))
    for p in participants:
        pc, ptsc = p_cols[p.id]
        _cell(ws, 3, pc,   "Pick", fill=PatternFill("solid", fgColor="BDD7EE"), font=BOLD)
        _cell(ws, 3, ptsc, "Pts",  fill=PatternFill("solid", fgColor="BDD7EE"), font=BOLD)
    ws.row_dimensions[3].height = 20

    # ── Data rows ─────────────────────────────────────────────────────────────
    data_row = 4
    current_round = None
    round_start = {}  # round → first data row
    round_total_rows = {}  # round → totals row

    for m in matches:
        # Section header when round changes
        if m.round != current_round:
            current_round = m.round
            ws.merge_cells(start_row=data_row, start_column=1, end_row=data_row, end_column=total_cols)
            _cell(ws, data_row, 1, ROUND_LABELS.get(m.round, m.round),
                  fill=HDR_FILL, font=WHITE_FONT, align="left")
            ws.row_dimensions[data_row].height = 22
            data_row += 1
            round_start[m.round] = data_row

        home = m.home_team.name if m.home_team else m.home_team_placeholder or "TBD"
        away = m.away_team.name if m.away_team else m.away_team_placeholder or "TBD"
        result = f"{m.home_score}–{m.away_score}" if m.is_finished else "—"

        _cell(ws, data_row, 1, m.match_number, fill=MATCH_FILL, font=BOLD)
        _cell(ws, data_row, 2, ROUND_LABELS.get(m.round, m.round), fill=MATCH_FILL)
        _cell(ws, data_row, 3, home, fill=MATCH_FILL, align="left")
        _cell(ws, data_row, 4, away, fill=MATCH_FILL, align="left")
        _cell(ws, data_row, 5, result, fill=RESULT_FILL, font=BOLD)

        for p in participants:
            pc, ptsc = p_cols[p.id]
            pred = pred_map.get((m.id, p.id))
            if pred:
                pick = f"{pred.home_score}–{pred.away_score}"
                pts  = pred.points if pred.points is not None else ""
                if m.is_finished:
                    pfill = EXACT_FILL if pts == 9 else (WINNER_FILL if pts == 7 else (WINNER_FILL if pts == 5 else WRONG_FILL))
                else:
                    pfill = None
                _cell(ws, data_row, pc,   pick, fill=pfill)
                _cell(ws, data_row, ptsc, pts,  fill=pfill, font=BOLD if pts else None)
            else:
                _cell(ws, data_row, pc,   "—")
                _cell(ws, data_row, ptsc, "")

        data_row += 1

    # ── Totals row ────────────────────────────────────────────────────────────
    data_row += 1
    ws.merge_cells(start_row=data_row, start_column=1, end_row=data_row, end_column=FIXED)
    _cell(ws, data_row, 1, "TOTAL POINTS", fill=HDR_FILL, font=WHITE_FONT, align="right")
    for p in participants:
        pc, ptsc = p_cols[p.id]
        total = sum(
            (pred_map[(m.id, p.id)].points or 0)
            for m in matches
            if (m.id, p.id) in pred_map and pred_map[(m.id, p.id)].points is not None
        )
        ws.merge_cells(start_row=data_row, start_column=pc, end_row=data_row, end_column=ptsc)
        _cell(ws, data_row, pc, total,
              fill=PatternFill("solid", fgColor="FFD700"), font=Font(bold=True, size=12))
    ws.row_dimensions[data_row].height = 25

    # ── Column widths ─────────────────────────────────────────────────────────
    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 8
    for p in participants:
        pc, ptsc = p_cols[p.id]
        ws.column_dimensions[get_column_letter(pc)].width   = 9
        ws.column_dimensions[get_column_letter(ptsc)].width = 5
    ws.freeze_panes = "F4"

    # ── Sheet 2: Leaderboard ─────────────────────────────────────────────────
    ws2 = wb.create_sheet("Leaderboard")
    headers = ["Rank", "Name", "Email", "Group Stage", "Round of 32",
               "Round of 16", "Quarterfinals", "Semifinals", "Final", "TOTAL"]
    for col, h in enumerate(headers, 1):
        _cell(ws2, 1, col, h, fill=PatternFill("solid", fgColor="1F4E79"), font=WHITE_FONT)

    scores = {}
    for p in participants:
        by_round = {}
        for m in matches:
            pred = pred_map.get((m.id, p.id))
            if pred and pred.points is not None:
                by_round[m.round] = by_round.get(m.round, 0) + pred.points
        scores[p.id] = {"name": p.name, "email": p.email, "by_round": by_round,
                        "total": sum(by_round.values())}

    ranked = sorted(scores.values(), key=lambda x: x["total"], reverse=True)
    for row, s in enumerate(ranked, 2):
        br = s["by_round"]
        vals = [row-1, s["name"], s["email"],
                br.get("group_stage",0), br.get("round_of_32",0),
                br.get("round_of_16",0), br.get("qf",0),
                br.get("sf",0), br.get("final",0), s["total"]]
        for col, v in enumerate(vals, 1):
            fill = PatternFill("solid", fgColor="FFD700") if col == 10 else None
            font = Font(bold=True) if col in (1, 10) else None
            _cell(ws2, row, col, v, fill=fill, font=font)

    for col, w in zip(range(1, 11), [6, 24, 28, 13, 13, 13, 14, 12, 8, 8]):
        ws2.column_dimensions[get_column_letter(col)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


@router.get("/export/excel")
def export_excel(db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    data = build_excel(db)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=quiniela-mundial-2026.xlsx"},
    )
