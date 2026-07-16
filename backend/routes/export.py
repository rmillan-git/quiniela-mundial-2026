import io
import smtplib
import traceback
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from database import get_db, settings
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

F_DARK_BLUE  = PatternFill("solid", fgColor="1F4E79")
F_MED_BLUE   = PatternFill("solid", fgColor="2E75B6")
F_LIGHT_BLUE = PatternFill("solid", fgColor="BDD7EE")
F_ROW        = PatternFill("solid", fgColor="D6E4F0")
F_RESULT     = PatternFill("solid", fgColor="E2EFDA")
F_EXACT      = PatternFill("solid", fgColor="C6EFCE")
F_WINNER     = PatternFill("solid", fgColor="DDEBF7")
F_WRONG      = PatternFill("solid", fgColor="FCE4D6")
F_GOLD       = PatternFill("solid", fgColor="FFD700")

WHITE_BOLD = Font(color="FFFFFF", bold=True)
BOLD       = Font(bold=True)
thin       = Side(style="thin")
BORDER     = Border(left=thin, right=thin, top=thin, bottom=thin)


def _c(ws, row, col, value="", fill=None, font=None, align="center"):
    c = ws.cell(row=row, column=col, value=value)
    if fill:  c.fill = fill
    if font:  c.font = font
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    c.border = BORDER
    return c


def _merge(ws, r1, c1, r2, c2):
    ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)


def build_excel(db: Session) -> bytes:
    wb = Workbook()

    participants = (
        db.query(Participant)
        .filter_by(is_approved=True, is_admin=False)
        .order_by(Participant.name)
        .all()
    )
    matches  = db.query(Match).order_by(Match.match_number).all()
    preds    = db.query(Prediction).all()
    pred_map = {(p.match_id, p.participant_id): p for p in preds}

    FIXED = 5
    p_pred_col = {p.id: FIXED + 1 + i * 2 for i, p in enumerate(participants)}
    p_pts_col  = {p.id: FIXED + 2 + i * 2 for i, p in enumerate(participants)}
    total_cols = FIXED + max(len(participants) * 2, 1)

    ws = wb.active
    ws.title = "Predictions"

    # Row 1 — title
    _merge(ws, 1, 1, 1, total_cols)
    c = ws.cell(row=1, column=1, value="⚽ Quiniela Mundial 2026 — Full Predictions")
    c.fill = F_DARK_BLUE
    c.font = Font(color="FFFFFF", bold=True, size=13)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # Row 2 — column headers
    for col, lbl in [(1,"#"),(2,"Round"),(3,"Home Team"),(4,"Away Team"),(5,"Result")]:
        _c(ws, 2, col, lbl, fill=F_MED_BLUE, font=WHITE_BOLD)
    for p in participants:
        pc, ptsc = p_pred_col[p.id], p_pts_col[p.id]
        _merge(ws, 2, pc, 2, ptsc)
        _c(ws, 2, pc, p.name, fill=F_MED_BLUE, font=WHITE_BOLD)
    ws.row_dimensions[2].height = 32

    # Row 3 — sub-header Pick / Pts
    for col in range(1, FIXED + 1):
        _c(ws, 3, col, "", fill=F_LIGHT_BLUE)
    for p in participants:
        _c(ws, 3, p_pred_col[p.id], "Pick", fill=F_LIGHT_BLUE, font=BOLD)
        _c(ws, 3, p_pts_col[p.id],  "Pts",  fill=F_LIGHT_BLUE, font=BOLD)
    ws.row_dimensions[3].height = 18

    # Data rows
    row = 4
    current_round = None
    for m in matches:
        if m.round != current_round:
            current_round = m.round
            _merge(ws, row, 1, row, total_cols)
            c = ws.cell(row=row, column=1, value=ROUND_LABELS.get(m.round, m.round))
            c.fill = F_DARK_BLUE; c.font = WHITE_BOLD
            c.alignment = Alignment(horizontal="left", vertical="center")
            c.border = BORDER
            ws.row_dimensions[row].height = 20
            row += 1

        home   = m.home_team.name if m.home_team else (m.home_team_placeholder or "TBD")
        away   = m.away_team.name if m.away_team else (m.away_team_placeholder or "TBD")
        result = f"{m.home_score}-{m.away_score}" if m.is_finished else "-"

        _c(ws, row, 1, m.match_number, fill=F_ROW, font=BOLD)
        _c(ws, row, 2, ROUND_LABELS.get(m.round, m.round), fill=F_ROW)
        _c(ws, row, 3, home, fill=F_ROW, align="left")
        _c(ws, row, 4, away, fill=F_ROW, align="left")
        _c(ws, row, 5, result, fill=F_RESULT, font=BOLD)

        for p in participants:
            pred = pred_map.get((m.id, p.id))
            pc   = p_pred_col[p.id]
            ptsc = p_pts_col[p.id]
            if pred:
                pick = f"{pred.home_score}-{pred.away_score}"
                pts  = pred.points
                if m.is_finished and pts is not None:
                    pf = F_EXACT if pts >= 9 else (F_WINNER if pts >= 5 else F_WRONG)
                else:
                    pf = None
                _c(ws, row, pc,   pick, fill=pf)
                _c(ws, row, ptsc, pts if pts is not None else "", fill=pf, font=BOLD if pts else None)
            else:
                _c(ws, row, pc,   "-")
                _c(ws, row, ptsc, "")
        row += 1

    # Totals row
    row += 1
    _merge(ws, row, 1, row, FIXED)
    c = ws.cell(row=row, column=1, value="TOTAL POINTS")
    c.fill = F_DARK_BLUE; c.font = WHITE_BOLD
    c.alignment = Alignment(horizontal="right", vertical="center")
    c.border = BORDER

    for p in participants:
        total = sum(
            pred_map[(m.id, p.id)].points or 0
            for m in matches
            if (m.id, p.id) in pred_map and pred_map[(m.id, p.id)].points is not None
        )
        pc, ptsc = p_pred_col[p.id], p_pts_col[p.id]
        _merge(ws, row, pc, row, ptsc)
        c = ws.cell(row=row, column=pc, value=total)
        c.fill = F_GOLD; c.font = Font(bold=True, size=12)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER
    ws.row_dimensions[row].height = 24

    # Column widths
    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 13
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 8
    for p in participants:
        ws.column_dimensions[get_column_letter(p_pred_col[p.id])].width = 8
        ws.column_dimensions[get_column_letter(p_pts_col[p.id])].width  = 5
    ws.freeze_panes = "F4"

    # ── Sheet 2: Leaderboard ─────────────────────────────────────────────────
    ws2 = wb.create_sheet("Leaderboard")
    hdrs = ["Rank","Name","Email","Group Stage","Round of 32","Round of 16",
            "Quarterfinals","Semifinals","Final","TOTAL"]
    for col, h in enumerate(hdrs, 1):
        _c(ws2, 1, col, h, fill=F_DARK_BLUE, font=WHITE_BOLD)
    ws2.row_dimensions[1].height = 22

    scores = []
    for p in participants:
        by_round = {}
        for m in matches:
            pred = pred_map.get((m.id, p.id))
            if pred and pred.points is not None:
                by_round[m.round] = by_round.get(m.round, 0) + pred.points
        scores.append({"name": p.name, "email": p.email, "by_round": by_round,
                       "total": sum(by_round.values())})
    scores.sort(key=lambda x: x["total"], reverse=True)

    for i, s in enumerate(scores, 1):
        br = s["by_round"]
        vals = [i, s["name"], s["email"],
                br.get("group_stage",0), br.get("round_of_32",0), br.get("round_of_16",0),
                br.get("qf",0), br.get("sf",0), br.get("final",0), s["total"]]
        for col, v in enumerate(vals, 1):
            fill = F_GOLD if col == 10 else None
            font = Font(bold=True) if col in (1, 10) else None
            _c(ws2, i + 1, col, v, fill=fill, font=font)

    for col, w in zip(range(1, 11), [6, 24, 28, 13, 13, 13, 14, 12, 8, 10]):
        ws2.column_dimensions[get_column_letter(col)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/export/excel")
def export_excel(db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    try:
        data = build_excel(db)
    except Exception as e:
        raise HTTPException(500, detail=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=quiniela-mundial-2026.xlsx"},
    )


@router.post("/send-report")
def send_report(db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    if not settings.gmail_user or not settings.gmail_app_password:
        raise HTTPException(500, "Gmail credentials not configured")

    try:
        excel_data = build_excel(db)
    except Exception as e:
        raise HTTPException(500, detail=f"Excel build failed: {e}")

    participants = (
        db.query(Participant)
        .filter_by(is_approved=True)
        .all()
    )
    recipients = [p.email for p in participants if p.email]
    today = datetime.now().strftime("%B %d, %Y")
    filename = f"quiniela-mundial-2026-{datetime.now().strftime('%Y-%m-%d')}.xlsx"

    # Build leaderboard summary for email body
    preds = db.query(Prediction).all()
    pred_map = {(p.match_id, p.participant_id): p for p in preds}
    matches = db.query(Match).all()
    scores = []
    for p in participants:
        if p.is_admin: continue
        total = sum(
            pred_map[(m.id, p.id)].points or 0
            for m in matches
            if (m.id, p.id) in pred_map and pred_map[(m.id, p.id)].points is not None
        )
        scores.append((p.name, total))
    scores.sort(key=lambda x: x[1], reverse=True)

    standings_html = "".join(
        f"<tr><td>{i}</td><td>{name}</td><td><b>{pts}</b></td></tr>"
        for i, (name, pts) in enumerate(scores, 1)
    )

    html_body = f"""
    <html><body>
    <h2>⚽ Quiniela Mundial 2026 — Daily Report</h2>
    <p>{today}</p>
    <h3>📊 Current Standings</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
      <tr style="background:#1F4E79;color:white"><th>#</th><th>Name</th><th>Points</th></tr>
      {standings_html}
    </table>
    <p>See the full predictions and results in the attached Excel file.</p>
    <p>🌍 <a href="https://quiniela-frontend-l8j1.onrender.com">View Leaderboard</a></p>
    </body></html>
    """

    sent = 0
    failed = []
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(settings.gmail_user, settings.gmail_app_password)

        for recipient in recipients:
            try:
                msg = MIMEMultipart()
                msg["From"] = settings.gmail_user
                msg["To"] = recipient
                msg["Subject"] = f"⚽ Quiniela Mundial 2026 — Daily Report {today}"
                msg.attach(MIMEText(html_body, "html"))

                part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                part.set_payload(excel_data)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={filename}")
                msg.attach(part)

                server.sendmail(settings.gmail_user, recipient, msg.as_string())
                sent += 1
            except Exception as e:
                failed.append(f"{recipient}: {e}")

        server.quit()
    except Exception as e:
        raise HTTPException(500, detail=f"SMTP error: {e}")

    return {"sent": sent, "failed": failed, "recipients": recipients}


GROUPS = list("ABCDEFGHIJKL")


def _simulate_group(group_matches: list, participant_id: int, pred_map: dict) -> list[dict]:
    """
    Returns [{name, flag, pts, gf, ga, gd, wins, draws, losses}, ...]
    sorted by simulated group standing from a participant's predictions.
    """
    stats: dict[int, dict] = {}  # team_id → stats

    def init(team_id, name, flag):
        if team_id not in stats:
            stats[team_id] = {"name": name, "flag": flag,
                               "pts": 0, "gf": 0, "ga": 0,
                               "wins": 0, "draws": 0, "losses": 0}

    for m in group_matches:
        if not m.home_team_id or not m.away_team_id:
            continue
        pred = pred_map.get((m.id, participant_id))
        if not pred:
            continue
        ph, pa = pred.home_score, pred.away_score
        init(m.home_team_id, m.home_team.name, m.home_team.flag_emoji)
        init(m.away_team_id, m.away_team.name, m.away_team.flag_emoji)
        stats[m.home_team_id]["gf"] += ph
        stats[m.home_team_id]["ga"] += pa
        stats[m.away_team_id]["gf"] += pa
        stats[m.away_team_id]["ga"] += ph
        if ph > pa:
            stats[m.home_team_id]["pts"] += 3
            stats[m.home_team_id]["wins"] += 1
            stats[m.away_team_id]["losses"] += 1
        elif pa > ph:
            stats[m.away_team_id]["pts"] += 3
            stats[m.away_team_id]["wins"] += 1
            stats[m.home_team_id]["losses"] += 1
        else:
            stats[m.home_team_id]["pts"] += 1
            stats[m.away_team_id]["pts"] += 1
            stats[m.home_team_id]["draws"] += 1
            stats[m.away_team_id]["draws"] += 1

    for s in stats.values():
        s["gd"] = s["gf"] - s["ga"]

    return sorted(stats.values(), key=lambda x: (x["pts"], x["gd"], x["gf"]), reverse=True)


def build_bracket_excel(db: Session) -> bytes:
    """
    Builds a bracket-based Excel:
    - Sheet 1 "Clasificados": summary showing who each participant predicted to
      advance (1st / 2nd) from each of the 12 groups, derived from their group
      stage score predictions.
    - One sheet per participant: group-by-group predictions + simulated standing
      + their knockout round predictions.
    """
    wb = Workbook()

    participants = (
        db.query(Participant)
        .filter_by(is_approved=True, is_admin=False)
        .order_by(Participant.name)
        .all()
    )
    all_matches = db.query(Match).order_by(Match.match_number).all()
    preds       = db.query(Prediction).all()
    pred_map    = {(p.match_id, p.participant_id): p for p in preds}

    group_matches: dict[str, list] = {g: [] for g in GROUPS}
    ko_matches:    list            = []
    for m in all_matches:
        if m.round == "group_stage" and m.group:
            group_matches[m.group].append(m)
        elif m.round != "group_stage":
            ko_matches.append(m)

    # ── Sheet 1: Clasificados (summary) ──────────────────────────────────────
    ws = wb.active
    ws.title = "Clasificados"

    # Title
    total_cols = 1 + len(GROUPS) * 3
    _merge(ws, 1, 1, 1, total_cols)
    c = ws.cell(row=1, column=1, value="⚽ Quiniela 2026 — Clasificados Predichos por Participante")
    c.fill = F_DARK_BLUE; c.font = Font(color="FFFFFF", bold=True, size=13)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    # Group headers
    ws.cell(row=2, column=1, value="Participante").fill = F_MED_BLUE
    ws.cell(row=2, column=1).font = WHITE_BOLD
    ws.cell(row=2, column=1).border = BORDER
    ws.cell(row=2, column=1).alignment = Alignment(horizontal="center", vertical="center")
    col = 2
    for g in GROUPS:
        _merge(ws, 2, col, 2, col + 2)
        c = ws.cell(row=2, column=col, value=f"Grupo {g}")
        c.fill = F_MED_BLUE; c.font = WHITE_BOLD
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER
        for sub, lbl in enumerate(["1°", "2°", "3°"]):
            _c(ws, 3, col + sub, lbl, fill=F_LIGHT_BLUE, font=BOLD)
        col += 3
    ws.row_dimensions[2].height = 22
    ws.row_dimensions[3].height = 18

    # Actual group advances (real results) — row 4
    _merge(ws, 4, 1, 4, 1)
    c = ws.cell(row=4, column=1, value="✅ REAL")
    c.fill = F_RESULT; c.font = BOLD
    c.alignment = Alignment(horizontal="center", vertical="center"); c.border = BORDER
    col = 2
    for g in GROUPS:
        gm = group_matches[g]
        # Build real standings from finished matches
        real_stats: dict[int, dict] = {}
        def _init_real(tid, name, flag):
            if tid not in real_stats:
                real_stats[tid] = {"name": name, "flag": flag, "pts": 0, "gf": 0, "ga": 0, "gd": 0}
        for m in gm:
            if not m.is_finished or m.home_team_id is None or m.away_team_id is None:
                continue
            _init_real(m.home_team_id, m.home_team.name, m.home_team.flag_emoji)
            _init_real(m.away_team_id, m.away_team.name, m.away_team.flag_emoji)
            real_stats[m.home_team_id]["gf"] += m.home_score
            real_stats[m.home_team_id]["ga"] += m.away_score
            real_stats[m.away_team_id]["gf"] += m.away_score
            real_stats[m.away_team_id]["ga"] += m.home_score
            if m.home_score > m.away_score:
                real_stats[m.home_team_id]["pts"] += 3
            elif m.away_score > m.home_score:
                real_stats[m.away_team_id]["pts"] += 3
            else:
                real_stats[m.home_team_id]["pts"] += 1
                real_stats[m.away_team_id]["pts"] += 1
        for s in real_stats.values():
            s["gd"] = s["gf"] - s["ga"]
        real_sorted = sorted(real_stats.values(), key=lambda x: (x["pts"], x["gd"], x["gf"]), reverse=True)
        for pos in range(3):
            name = (real_sorted[pos]["flag"] + " " + real_sorted[pos]["name"]) if pos < len(real_sorted) else "—"
            fill = F_RESULT if pos < 2 else None
            _c(ws, 4, col + pos, name, fill=fill)
        col += 3

    # Per-participant rows
    row = 5
    for p in participants:
        _c(ws, row, 1, p.name, fill=F_ROW, align="left", font=BOLD)
        col = 2
        for g in GROUPS:
            standing = _simulate_group(group_matches[g], p.id, pred_map)
            for pos in range(3):
                if pos < len(standing):
                    team = standing[pos]
                    cell_val = f"{team['flag']} {team['name']} ({team['pts']}pts)"
                else:
                    cell_val = "—"
                fill = F_LIGHT_BLUE if pos < 2 else None
                _c(ws, row, col + pos, cell_val, fill=fill, align="left")
            col += 3
        row += 1

    # Column widths for summary sheet
    ws.column_dimensions["A"].width = 20
    for i, g in enumerate(GROUPS):
        base = 2 + i * 3
        for offset in range(3):
            ws.column_dimensions[get_column_letter(base + offset)].width = 22
    ws.freeze_panes = "B5"

    # ── Per-participant sheets ────────────────────────────────────────────────
    F_GRP_WIN  = PatternFill("solid", fgColor="C6EFCE")  # green  — 1st place
    F_GRP_2ND  = PatternFill("solid", fgColor="DDEBF7")  # blue   — 2nd place
    F_GRP_3RD  = PatternFill("solid", fgColor="FFFACD")  # yellow — 3rd
    F_GRP_4TH  = PatternFill("solid", fgColor="FCE4D6")  # red    — 4th

    PLACE_FILLS = [F_GRP_WIN, F_GRP_2ND, F_GRP_3RD, F_GRP_4TH]

    for p in participants:
        sheet_name = p.name[:31].replace("/", "-").replace("\\", "-").replace("?", "").replace("*", "").replace("[", "").replace("]", "").replace(":", "-")
        ws2 = wb.create_sheet(title=sheet_name)

        # Title
        _merge(ws2, 1, 1, 1, 8)
        c = ws2.cell(row=1, column=1, value=f"⚽ Quiniela de {p.name} — Bracket por Grupo")
        c.fill = F_DARK_BLUE; c.font = Font(color="FFFFFF", bold=True, size=12)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws2.row_dimensions[1].height = 26

        row = 2
        total_pts = 0

        # ── Group stage section ──
        for g in GROUPS:
            gm = group_matches[g]
            standing = _simulate_group(gm, p.id, pred_map)

            # Group header
            _merge(ws2, row, 1, row, 8)
            c = ws2.cell(row=row, column=1, value=f"GRUPO {g}")
            c.fill = F_MED_BLUE; c.font = WHITE_BOLD
            c.alignment = Alignment(horizontal="left", vertical="center"); c.border = BORDER
            ws2.row_dimensions[row].height = 18
            row += 1

            # Match predictions
            _c(ws2, row, 1, "#", fill=F_LIGHT_BLUE, font=BOLD)
            _c(ws2, row, 2, "Local", fill=F_LIGHT_BLUE, font=BOLD, align="left")
            _c(ws2, row, 3, "Predicción", fill=F_LIGHT_BLUE, font=BOLD)
            _c(ws2, row, 4, "Resultado Real", fill=F_LIGHT_BLUE, font=BOLD)
            _c(ws2, row, 5, "Pts", fill=F_LIGHT_BLUE, font=BOLD)
            _c(ws2, row, 6, "", fill=F_LIGHT_BLUE)
            _c(ws2, row, 7, "", fill=F_LIGHT_BLUE)
            _c(ws2, row, 8, "Visita", fill=F_LIGHT_BLUE, font=BOLD, align="left")
            row += 1

            for m in gm:
                pred = pred_map.get((m.id, p.id))
                home = m.home_team.name if m.home_team else "TBD"
                away = m.away_team.name if m.away_team else "TBD"
                pick = f"{pred.home_score}–{pred.away_score}" if pred else "—"
                real = f"{m.home_score}–{m.away_score}" if m.is_finished else "—"
                pts  = pred.points if pred else None
                if pts:
                    total_pts += pts
                pf = (F_EXACT if pts and pts >= 9 else F_WINNER if pts and pts >= 5 else F_WRONG if (m.is_finished and pred) else None)
                _c(ws2, row, 1, m.match_number, fill=pf, font=BOLD)
                _c(ws2, row, 2, home, fill=pf, align="left")
                _c(ws2, row, 3, pick, fill=pf, font=BOLD)
                _c(ws2, row, 4, real, fill=pf, font=BOLD if m.is_finished else None)
                _c(ws2, row, 5, pts if pts is not None else "", fill=pf, font=Font(bold=True) if pts else None)
                _c(ws2, row, 6, "", fill=pf)
                _c(ws2, row, 7, "", fill=pf)
                _c(ws2, row, 8, away, fill=pf, align="left")
                row += 1

            # Simulated group standing
            _merge(ws2, row, 1, row, 8)
            c = ws2.cell(row=row, column=1, value=f"→ Tabla simulada Grupo {g} (según sus predicciones)")
            c.fill = F_RESULT; c.font = Font(italic=True, bold=True)
            c.alignment = Alignment(horizontal="left", vertical="center"); c.border = BORDER
            ws2.row_dimensions[row].height = 16
            row += 1

            for pos, s in enumerate(standing):
                place_fill = PLACE_FILLS[pos] if pos < 4 else None
                place_lbl = ["🥇 1°", "🥈 2°", "🥉 3°", "4°"][pos] if pos < 4 else f"{pos+1}°"
                _c(ws2, row, 1, place_lbl, fill=place_fill, font=BOLD)
                _c(ws2, row, 2, f"{s['flag']} {s['name']}", fill=place_fill, align="left")
                _c(ws2, row, 3, f"{s['pts']} pts", fill=place_fill, font=BOLD)
                _c(ws2, row, 4, f"GD {s['gd']:+d}", fill=place_fill)
                _c(ws2, row, 5, f"GF {s['gf']}", fill=place_fill)
                _c(ws2, row, 6, f"GA {s['ga']}", fill=place_fill)
                _c(ws2, row, 7, f"{s['wins']}G {s['draws']}E {s['losses']}P", fill=place_fill)
                _c(ws2, row, 8, "✅ PASA" if pos < 2 else ("🔶 posible 3°" if pos == 2 else "❌"), fill=place_fill)
                row += 1

            row += 1  # blank row between groups

        # ── Knockout predictions section ──
        if ko_matches:
            _merge(ws2, row, 1, row, 8)
            c = ws2.cell(row=row, column=1, value="RONDAS ELIMINATORIAS — Predicciones Originales")
            c.fill = F_DARK_BLUE; c.font = WHITE_BOLD
            c.alignment = Alignment(horizontal="left", vertical="center"); c.border = BORDER
            ws2.row_dimensions[row].height = 20
            row += 1

            _c(ws2, row, 1, "#", fill=F_LIGHT_BLUE, font=BOLD)
            _c(ws2, row, 2, "Ronda", fill=F_LIGHT_BLUE, font=BOLD)
            _c(ws2, row, 3, "Local Real", fill=F_LIGHT_BLUE, font=BOLD, align="left")
            _c(ws2, row, 4, "Predicción", fill=F_LIGHT_BLUE, font=BOLD)
            _c(ws2, row, 5, "Resultado Real", fill=F_LIGHT_BLUE, font=BOLD)
            _c(ws2, row, 6, "Pts", fill=F_LIGHT_BLUE, font=BOLD)
            _c(ws2, row, 7, "Visita Real", fill=F_LIGHT_BLUE, font=BOLD, align="left")
            _c(ws2, row, 8, "Nota", fill=F_LIGHT_BLUE, font=BOLD)
            row += 1

            current_round = None
            for m in ko_matches:
                if m.round != current_round:
                    current_round = m.round
                    _merge(ws2, row, 1, row, 8)
                    c = ws2.cell(row=row, column=1, value=ROUND_LABELS.get(m.round, m.round).upper())
                    c.fill = F_MED_BLUE; c.font = WHITE_BOLD
                    c.alignment = Alignment(horizontal="left", vertical="center"); c.border = BORDER
                    ws2.row_dimensions[row].height = 16
                    row += 1

                pred  = pred_map.get((m.id, p.id))
                home  = m.home_team.name if m.home_team else (m.home_team_placeholder or "TBD")
                away  = m.away_team.name if m.away_team else (m.away_team_placeholder or "TBD")
                pick  = f"{pred.home_score}–{pred.away_score}" if pred else "—"
                real  = f"{m.home_score}–{m.away_score}" if m.is_finished else "—"
                pts   = pred.points if pred else None
                if pts:
                    total_pts += pts
                pf = (F_EXACT if pts and pts >= 9 else F_WINNER if pts and pts >= 5 else F_WRONG if (m.is_finished and pred) else None)
                note = "⚠️ equipos TBD al predecir" if not (m.home_team and m.away_team) and pred else ""
                _c(ws2, row, 1, m.match_number, fill=pf, font=BOLD)
                _c(ws2, row, 2, ROUND_LABELS.get(m.round, m.round), fill=pf)
                _c(ws2, row, 3, home, fill=pf, align="left")
                _c(ws2, row, 4, pick, fill=pf, font=BOLD)
                _c(ws2, row, 5, real, fill=pf, font=BOLD if m.is_finished else None)
                _c(ws2, row, 6, pts if pts is not None else "", fill=pf, font=Font(bold=True) if pts else None)
                _c(ws2, row, 7, away, fill=pf, align="left")
                _c(ws2, row, 8, note, fill=pf)
                row += 1

        # Totals
        row += 1
        _merge(ws2, row, 1, row, 7)
        c = ws2.cell(row=row, column=1, value="TOTAL PUNTOS (calculado automáticamente)")
        c.fill = F_DARK_BLUE; c.font = WHITE_BOLD
        c.alignment = Alignment(horizontal="right", vertical="center"); c.border = BORDER
        c2 = ws2.cell(row=row, column=8, value=total_pts)
        c2.fill = F_GOLD; c2.font = Font(bold=True, size=12)
        c2.alignment = Alignment(horizontal="center", vertical="center"); c2.border = BORDER
        ws2.row_dimensions[row].height = 22

        # Column widths
        for col_i, w in enumerate([5, 20, 22, 12, 14, 6, 22, 28], 1):
            ws2.column_dimensions[get_column_letter(col_i)].width = w
        ws2.freeze_panes = "A3"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/export/bracket")
def export_bracket(db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    """Export bracket-based Excel: predicted group advances + per-participant bracket view."""
    try:
        data = build_bracket_excel(db)
    except Exception as e:
        raise HTTPException(500, detail=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=quiniela-2026-bracket.xlsx"},
    )


def build_by_participant_excel(db: Session) -> bytes:
    """One sheet per participant showing their original predictions vs actual results."""
    wb = Workbook()
    wb.remove(wb.active)  # remove default empty sheet

    participants = (
        db.query(Participant)
        .filter_by(is_approved=True, is_admin=False)
        .order_by(Participant.name)
        .all()
    )
    matches  = db.query(Match).order_by(Match.match_number).all()
    preds    = db.query(Prediction).all()
    pred_map = {(p.match_id, p.participant_id): p for p in preds}

    HDRS = ["#", "Ronda", "Local", "Visita", "Tu Predicción", "Resultado Real", "Puntos"]
    COL_WIDTHS = [5, 14, 22, 22, 14, 14, 8]

    F_SECTION  = PatternFill("solid", fgColor="1F4E79")
    F_HEADER   = PatternFill("solid", fgColor="2E75B6")
    F_ROW_ODD  = PatternFill("solid", fgColor="EBF3FB")
    F_EXACT    = PatternFill("solid", fgColor="C6EFCE")  # green  — exact score
    F_WINNER   = PatternFill("solid", fgColor="DDEBF7")  # blue   — correct winner
    F_WRONG    = PatternFill("solid", fgColor="FCE4D6")  # orange — wrong
    F_PENDING  = PatternFill("solid", fgColor="FFFACD")  # yellow — no result yet
    F_NO_PRED  = PatternFill("solid", fgColor="F0F0F0")  # grey   — no prediction

    def row_fill(pred, match):
        if not match.is_finished:
            return F_PENDING if pred else F_NO_PRED
        if not pred:
            return F_NO_PRED
        pts = pred.points
        if pts is None:
            return None
        if pts >= 9:
            return F_EXACT
        if pts >= 5:
            return F_WINNER
        return F_WRONG

    for p in participants:
        # Sheet name max 31 chars, no special chars
        sheet_name = p.name[:31].replace("/", "-").replace("\\", "-").replace("?", "").replace("*", "").replace("[", "").replace("]", "").replace(":", "-")
        ws = wb.create_sheet(title=sheet_name)

        # Title row
        _merge(ws, 1, 1, 1, 7)
        c = ws.cell(row=1, column=1, value=f"⚽ Quiniela Mundial 2026 — {p.name}")
        c.fill = F_SECTION
        c.font = Font(color="FFFFFF", bold=True, size=12)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 26

        # Header row
        for col, (lbl, w) in enumerate(zip(HDRS, COL_WIDTHS), 1):
            _c(ws, 2, col, lbl, fill=F_HEADER, font=WHITE_BOLD)
            ws.column_dimensions[get_column_letter(col)].width = w
        ws.row_dimensions[2].height = 20

        row = 3
        current_round = None
        total_pts = 0
        for m in matches:
            if m.round != current_round:
                current_round = m.round
                _merge(ws, row, 1, row, 7)
                c = ws.cell(row=row, column=1, value=ROUND_LABELS.get(m.round, m.round).upper())
                c.fill = F_SECTION
                c.font = Font(color="FFFFFF", bold=True)
                c.alignment = Alignment(horizontal="left", vertical="center")
                c.border = BORDER
                ws.row_dimensions[row].height = 18
                row += 1

            pred  = pred_map.get((m.id, p.id))
            home  = m.home_team.name if m.home_team else (m.home_team_placeholder or "TBD")
            away  = m.away_team.name if m.away_team else (m.away_team_placeholder or "TBD")
            real  = f"{m.home_score}–{m.away_score}" if m.is_finished else "—"
            pick  = f"{pred.home_score}–{pred.away_score}" if pred else "—"
            pts   = pred.points if pred else None
            if pts:
                total_pts += pts

            rf = row_fill(pred, m)
            odd = (row % 2 == 1)
            base_fill = rf if rf else (F_ROW_ODD if odd else None)

            _c(ws, row, 1, m.match_number, fill=base_fill, font=BOLD)
            _c(ws, row, 2, ROUND_LABELS.get(m.round, m.round), fill=base_fill)
            _c(ws, row, 3, home, fill=base_fill, align="left")
            _c(ws, row, 4, away, fill=base_fill, align="left")
            _c(ws, row, 5, pick, fill=base_fill, font=BOLD)
            _c(ws, row, 6, real, fill=base_fill, font=BOLD if m.is_finished else None)
            _c(ws, row, 7, pts if pts is not None else "", fill=base_fill,
               font=Font(bold=True) if pts is not None else None)
            row += 1

        # Totals row
        row += 1
        _merge(ws, row, 1, row, 6)
        c = ws.cell(row=row, column=1, value="TOTAL PUNTOS")
        c.fill = F_SECTION; c.font = WHITE_BOLD
        c.alignment = Alignment(horizontal="right", vertical="center")
        c.border = BORDER
        c2 = ws.cell(row=row, column=7, value=total_pts)
        c2.fill = F_GOLD; c2.font = Font(bold=True, size=12)
        c2.alignment = Alignment(horizontal="center", vertical="center")
        c2.border = BORDER
        ws.row_dimensions[row].height = 22

        ws.freeze_panes = "A3"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/export/by-participant")
def export_by_participant(db: Session = Depends(get_db), _: Participant = Depends(get_current_admin)):
    """Export one sheet per participant with their original predictions vs real results."""
    try:
        data = build_by_participant_excel(db)
    except Exception as e:
        raise HTTPException(500, detail=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=quiniela-2026-por-participante.xlsx"},
    )


@router.get("/cron/ping")
def cron_ping():
    """Public keep-alive endpoint — call every 10 min to prevent Render free tier sleep."""
    return {"status": "alive"}


@router.get("/cron/daily-report")
def cron_daily_report(token: str = Query(...), db: Session = Depends(get_db)):
    """Send daily report triggered by external cron service (cron-job.org)."""
    if not settings.cron_secret or token != settings.cron_secret:
        raise HTTPException(403, "Invalid token")
    return send_report(db)
