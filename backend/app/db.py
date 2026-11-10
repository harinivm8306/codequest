"""Database: SQLite by default (zero setup), PostgreSQL when DATABASE_URL points to one."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.config import settings


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


url = settings.database_url
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg://", 1)
elif url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("u"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16), default="citizen")  # citizen | sahayak
    phone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    profiles: Mapped[list[Profile]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("p"))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(80), default="")
    language: Mapped[str] = mapped_column(String(4), default="en")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    owner: Mapped[User] = relationship(back_populates="profiles")
    conversation: Mapped[Conversation] = relationship(back_populates="profile", cascade="all, delete-orphan", uselist=False)
    documents: Mapped[list[Document]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("c"))
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), unique=True)
    turns: Mapped[list] = mapped_column(JSON, default=list)
    state: Mapped[dict] = mapped_column(JSON, default=dict)  # pending question, pending confirmation
    language: Mapped[str] = mapped_column(String(4), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    profile: Mapped[Profile] = relationship(back_populates="conversation")


class Document(Base):
    """Extracted, masked facts from an uploaded image. The image itself is never stored."""

    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("d"))
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    doc_type: Mapped[str] = mapped_column(String(40))
    extracted: Mapped[dict] = mapped_column(JSON, default=dict)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(16), default="ocr")  # ocr | manual
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    profile: Mapped[Profile] = relationship(back_populates="documents")


class EligibilityRun(Base):
    """Audit log: rule version, a hash of the inputs, and the results. No personal fields."""

    __tablename__ = "eligibility_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("e"))
    profile_hash: Mapped[str] = mapped_column(String(64), index=True)
    rules_version: Mapped[str] = mapped_column(String(32))
    results: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
