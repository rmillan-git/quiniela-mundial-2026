import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from database import engine, SessionLocal
from models import Base
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    asyncio.create_task(_auto_sync())
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
