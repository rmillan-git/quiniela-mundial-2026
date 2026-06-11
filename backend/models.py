from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship
from database import Base


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    registered_at = Column(DateTime, default=datetime.utcnow)

    predictions = relationship("Prediction", back_populates="participant", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    group = Column(String(1), nullable=False)  # A-L
    flag_emoji = Column(String(10), default="🏳️")

    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    match_number = Column(Integer, unique=True, nullable=False)
    round = Column(String(30), nullable=False)  # group_stage, round_of_32, round_of_16, qf, sf, final
    group = Column(String(1), nullable=True)  # only for group stage
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    home_team_placeholder = Column(String(50), nullable=True)  # e.g. "Winner A1"
    away_team_placeholder = Column(String(50), nullable=True)
    kickoff_utc = Column(DateTime, nullable=False)
    venue = Column(String(100), nullable=True)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    is_finished = Column(Boolean, default=False)

    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    predictions = relationship("Prediction", back_populates="match")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    home_score = Column(Integer, nullable=False)
    away_score = Column(Integer, nullable=False)
    points = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    participant = relationship("Participant", back_populates="predictions")
    match = relationship("Match", back_populates="predictions")
