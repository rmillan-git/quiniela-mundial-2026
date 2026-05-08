import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from database import engine
from models import Base
from routes import auth, participants, matches, predictions, leaderboard


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    Base.metadata.create_all(bind=engine)
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


@app.get("/")
def root():
    return {"status": "ok", "app": "Quiniela Mundial 2026"}
