"""Compatibility shim that forwards to app.core.database."""

from app.core.database import Base, SessionLocal, engine


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
