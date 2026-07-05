import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from database import engine, SessionLocal, settings
from models import Base, Participant
from routes import auth, participants, matches, predictions, leaderboard, export, stats
from routes.matches import sync_results_from_api, _do_assign_ko_from_standings


def wait_for_db(retries: int = 15, delay: float = 2.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            with engine.connect():
                return
        except OperationalError:
            if attempt == retries:
                raise
            print(f"DB not ready, retrying ({attempt}/{retries})...")
            time.sleep(delay)


async def _auto_sync():
    """Sync World Cup results every 5 minutes in the background."""
    while True:
        await asyncio.sleep(300)
        try:
            db = SessionLocal()
            result = sync_results_from_api(db)
            if result.get("updated", 0) > 0:
                print(f"Auto-sync: updated {result['updated']} match(es)")
        except Exception as e:
            print(f"Auto-sync error: {e}")
        finally:
            db.close()


async def _daily_report():
    """Send daily email report at 8 AM CDT (13:00 UTC) every day."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email.mime.text import MIMEText
    from email import encoders
    from routes.export import build_excel

    while True:
        now_utc = datetime.now(timezone.utc)
        target = now_utc.replace(hour=13, minute=0, second=0, microsecond=0)
        if now_utc >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now_utc).total_seconds())

        if not settings.gmail_user or not settings.gmail_app_password:
            print("Daily report skipped — Gmail credentials not set")
            continue

        try:
            db = SessionLocal()
            excel_data = build_excel(db)
            recipients = [
                p.email for p in db.query(Participant).filter_by(is_approved=True, is_admin=False).all() if p.email
            ]
            today_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
            fname = f"quiniela-mundial-2026-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.xlsx"

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(settings.gmail_user, settings.gmail_app_password)
            for to in recipients:
                msg = MIMEMultipart()
                msg["From"] = settings.gmail_user
                msg["To"] = to
                msg["Subject"] = f"⚽ Quiniela Mundial 2026 — Daily Report {today_str}"
                msg.attach(MIMEText(
                    f"<html><body><h2>⚽ Quiniela Mundial 2026</h2>"
                    f"<p>Daily report for {today_str}. Full predictions and standings in the attached Excel file.</p>"
                    f"<p>🌍 <a href='https://quiniela-frontend-l8j1.onrender.com'>View Leaderboard</a></p>"
                    f"</body></html>", "html"
                ))
                part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                part.set_payload(excel_data)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={fname}")
                msg.attach(part)
                server.sendmail(settings.gmail_user, to, msg.as_string())
            server.quit()
            print(f"Daily report: sent to {len(recipients)} recipients")
        except Exception as e:
            print(f"Daily report error: {e}")
        finally:
            db.close()


def _migrate():
    """Add new columns and fix data without dropping existing data."""
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE matches ADD COLUMN IF NOT EXISTS winner_id INTEGER REFERENCES teams(id)"))
        conn.execute(text("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS predicted_winner_side VARCHAR(4)"))
        conn.execute(text("ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_score_final INTEGER"))
        conn.execute(text("ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_score_final INTEGER"))
        # Fix R16 bracket pairings — seed_data.py had consecutive-pair assumption; real FIFA bracket is:
        # M89=P74/P77, M90=P73/P75, M91=P76/P78, M92=P79/P80
        # M95=P85/P87 (Switzerland vs Colombia), M96=P86/P88 (Argentina vs Egypt)
        conn.execute(text("UPDATE matches SET home_team_placeholder='Ganador P74', away_team_placeholder='Ganador P77' WHERE match_number=89"))
        conn.execute(text("UPDATE matches SET home_team_placeholder='Ganador P73', away_team_placeholder='Ganador P75' WHERE match_number=90"))
        conn.execute(text("UPDATE matches SET home_team_placeholder='Ganador P76', away_team_placeholder='Ganador P78' WHERE match_number=91"))
        conn.execute(text("UPDATE matches SET home_team_placeholder='Ganador P85', away_team_placeholder='Ganador P87' WHERE match_number=95"))
        conn.execute(text("UPDATE matches SET home_team_placeholder='Ganador P86', away_team_placeholder='Ganador P88' WHERE match_number=96"))
        # Backfill final score for group stage (no ET possible)
        conn.execute(text(
            "UPDATE matches SET home_score_final = home_score, away_score_final = away_score "
            "WHERE round = 'group_stage' AND is_finished = TRUE AND home_score IS NOT NULL AND home_score_final IS NULL"
        ))
        # One-time fix: flip M100 (QF) predictions home↔away because the bracket correction
        # swapped Argentina (was away in M95) → home in M96, and Colombia home in M96 → away in M95.
        # M100 = winner M95 (home) vs winner M96 (away), so home/away in M100 also flipped.
        # Guard via m100_preds_flipped flag so this runs exactly once.
        conn.execute(text("ALTER TABLE matches ADD COLUMN IF NOT EXISTS m100_preds_flipped BOOLEAN DEFAULT FALSE"))
        row = conn.execute(text(
            "SELECT id FROM matches WHERE match_number = 100 AND (m100_preds_flipped IS NULL OR m100_preds_flipped = FALSE)"
        )).fetchone()
        if row:
            conn.execute(text("""
                UPDATE predictions
                SET home_score = away_score,
                    away_score = home_score,
                    predicted_winner_side = CASE
                        WHEN predicted_winner_side = 'home' THEN 'away'
                        WHEN predicted_winner_side = 'away' THEN 'home'
                        ELSE predicted_winner_side
                    END
                WHERE match_id = :mid AND points IS NULL
            """), {"mid": row[0]})
            conn.execute(text("UPDATE matches SET m100_preds_flipped = TRUE WHERE match_number = 100"))
            print("_migrate: flipped M100 predictions for bracket correction (one-time)")
        conn.commit()


def _fix_ko_kickoffs():
    """Fix R32 and R16 kickoff UTC times to match actual WC 2026 schedule.
    Runs on every startup — idempotent. ET = UTC-4 in Jun/Jul 2026."""
    from models import Match
    from datetime import datetime as dt

    db = SessionLocal()
    try:
        # ── R32 actual schedule (UTC naive) ──────────────────────────────────
        r32_sched = [
            ("South Africa", "Canada",       dt(2026,  6, 28, 19,  0)),  # Jun 28 3pm ET / 2pm CDT
            ("Brazil",       "Japan",        dt(2026,  6, 29, 17,  0)),  # Jun 29 1pm ET / 12pm CDT
            ("Germany",      "Paraguay",     dt(2026,  6, 29, 20, 30)),  # Jun 29 4:30pm ET / 3:30pm CDT
            ("Netherlands",  "Morocco",      dt(2026,  6, 30,  1,  0)),  # Jun 29 9pm ET / 8pm CDT
            ("Ivory Coast",  "Norway",       dt(2026,  6, 30, 17,  0)),  # Jun 30 1pm ET / 12pm CDT
            ("France",       "Sweden",       dt(2026,  6, 30, 21,  0)),  # Jun 30 5pm ET / 4pm CDT
            ("Mexico",       "Ecuador",      dt(2026,  7,  1,  1,  0)),  # Jun 30 9pm ET / 8pm CDT
            ("England",      "DR Congo",     dt(2026,  7,  1, 16,  0)),  # Jul 1 12pm ET / 11am CDT
            ("Belgium",      "Senegal",      dt(2026,  7,  1, 20,  0)),  # Jul 1 4pm ET / 3pm CDT
            ("USA",          "Bosnia",       dt(2026,  7,  2,  0,  0)),  # Jul 1 8pm ET / 7pm CDT
            ("Spain",        "Austria",      dt(2026,  7,  2, 19,  0)),  # Jul 2 3pm ET / 2pm CDT
            ("Portugal",     "Croatia",      dt(2026,  7,  2, 23,  0)),  # Jul 2 7pm ET / 6pm CDT
            ("Switzerland",  "Algeria",      dt(2026,  7,  3,  3,  0)),  # Jul 2 11pm ET / 10pm CDT
            ("Australia",    "Egypt",        dt(2026,  7,  3, 18,  0)),  # Jul 3 2pm ET / 1pm CDT
            ("Argentina",    "Cape Verde",   dt(2026,  7,  3, 22,  0)),  # Jul 3 6pm ET / 5pm CDT
            ("Colombia",     "Ghana",        dt(2026,  7,  4,  1, 30)),  # Jul 3 9:30pm ET / 8:30pm CDT
        ]

        def sub(a, b):
            a, b = a.lower().strip(), b.lower().strip()
            return a in b or b in a

        r32_matches = db.query(Match).filter(Match.round == "round_of_32").all()
        done_m, done_s = set(), set()

        # Pass 1: match by both team names
        for i, (h, a, kickoff) in enumerate(r32_sched):
            for m in r32_matches:
                if m.id in done_m:
                    continue
                hn = m.home_team.name if m.home_team else ""
                an = m.away_team.name if m.away_team else ""
                if (sub(h, hn) and sub(a, an)) or (sub(h, an) and sub(a, hn)):
                    m.kickoff_utc = kickoff
                    done_m.add(m.id)
                    done_s.add(i)
                    break

        # Pass 2: single-team fallback for games where one team isn't in our DB
        for i, (h, a, kickoff) in enumerate(r32_sched):
            if i in done_s:
                continue
            for m in r32_matches:
                if m.id in done_m:
                    continue
                hn = m.home_team.name if m.home_team else ""
                an = m.away_team.name if m.away_team else ""
                if sub(h, hn) or sub(a, hn) or sub(h, an) or sub(a, an):
                    m.kickoff_utc = kickoff
                    done_m.add(m.id)
                    done_s.add(i)
                    break

        # ── R16 actual schedule by match_number (confirmed from official bracket) ─
        r16_sched = {
            90: dt(2026, 7, 4, 17,  0),   # Jul 4 1pm ET / 12pm CDT — Canada vs Net/Mor
            89: dt(2026, 7, 4, 21,  0),   # Jul 4 5pm ET / 4pm CDT  — Ger/Par vs Fra/Swe
            91: dt(2026, 7, 5, 20,  0),   # Jul 5 4pm ET / 3pm CDT  — Bra/Jpn vs IvC/Nor
            92: dt(2026, 7, 6,  0,  0),   # Jul 5 8pm ET / 7pm CDT  — Mex/Ecu vs Eng/Cgo
            94: dt(2026, 7, 6, 19,  0),   # Jul 6 3pm ET / 2pm CDT  — Por/Cro vs Esp/Aut
            93: dt(2026, 7, 6, 21,  0),   # Jul 6 5pm ET / 4pm CDT  — USA/Bos vs Bel/Sen
            96: dt(2026, 7, 7, 16,  0),   # Jul 7 12pm ET / 11am CDT — Arg/CPV vs Aus/Egy
            95: dt(2026, 7, 7, 20,  0),   # Jul 7 4pm ET / 3pm CDT  — Sui/Alg vs Col/Gha
        }
        for mnum, kickoff in r16_sched.items():
            m = db.query(Match).filter(Match.match_number == mnum).first()
            if m:
                m.kickoff_utc = kickoff

        db.commit()
        print(f"_fix_ko_kickoffs: updated R32 ({len(done_m)} matches) and R16 kickoff times")
    except Exception as e:
        print(f"_fix_ko_kickoffs error: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    _migrate()
    _fix_ko_kickoffs()
    # Re-resolve KO team assignments after every migration (placeholder fixes need this)
    db = SessionLocal()
    try:
        _do_assign_ko_from_standings(db)
        db.commit()
    finally:
        db.close()
    asyncio.create_task(_auto_sync())
    asyncio.create_task(_daily_report())
    yield


app = FastAPI(title="Quiniela Mundial 2026", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(participants.router)
app.include_router(matches.router)
app.include_router(predictions.router)
app.include_router(leaderboard.router)
app.include_router(export.router)
app.include_router(stats.router)


@app.get("/")
def root():
    return {"status": "ok", "app": "Quiniela Mundial 2026"}
