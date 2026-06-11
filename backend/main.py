import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from database import engine, SessionLocal, settings
from models import Base, Participant
from routes import auth, participants, matches, predictions, leaderboard, export
from routes.matches import sync_results_from_api


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    Base.metadata.create_all(bind=engine)
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


@app.get("/")
def root():
    return {"status": "ok", "app": "Quiniela Mundial 2026"}
