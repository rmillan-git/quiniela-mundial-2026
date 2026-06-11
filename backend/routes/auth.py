from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database import get_db, settings
from models import Participant

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def get_current_participant(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Participant:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    participant = db.query(Participant).filter_by(email=email).first()
    if not participant:
        raise HTTPException(status_code=401, detail="User not found")
    return participant


def get_current_admin(current: Participant = Depends(get_current_participant)) -> Participant:
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return current


@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(Participant).filter_by(email=req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    p = Participant(
        name=req.name,
        email=req.email,
        hashed_password=pwd_context.hash(req.password),
        is_admin=False,
        is_approved=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "name": p.name, "email": p.email, "is_approved": p.is_approved}


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    p = db.query(Participant).filter_by(email=form.username).first()
    if not p or not pwd_context.verify(form.password, p.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not p.is_approved:
        raise HTTPException(status_code=403, detail="Account pending approval")
    return {"access_token": create_token({"sub": p.email}), "token_type": "bearer"}


@router.get("/me")
def me(current: Participant = Depends(get_current_participant)):
    return {
        "id": current.id,
        "name": current.name,
        "email": current.email,
        "is_admin": current.is_admin,
        "is_approved": current.is_approved,
    }


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.patch("/change-password")
def change_password(req: ChangePasswordRequest, current: Participant = Depends(get_current_participant), db: Session = Depends(get_db)):
    if not pwd_context.verify(req.current_password, current.hashed_password):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Mínimo 6 caracteres")
    current.hashed_password = pwd_context.hash(req.new_password)
    db.commit()
    return {"ok": True}
