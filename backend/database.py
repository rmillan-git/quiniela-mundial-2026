from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://quiniela:quiniela@localhost:5432/quiniela"
    secret_key: str = "dev-secret-key-change-in-prod"
    admin_email: str = "millan.ricardo@gmail.com"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    class Config:
        env_file = ".env"


settings = Settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
