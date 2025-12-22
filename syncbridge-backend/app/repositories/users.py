from datetime import datetime
from sqlalchemy.orm import Session

from app.models import User
from app.utils import get_password_hash, verify_password


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


# Backward-compatible alias
get_user = get_by_id


def create(db: Session, email: str, password: str, display_name: str | None = None) -> User:
    now = datetime.utcnow()
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        display_name=display_name or email.split("@")[0],
        role=None,
        is_active=0,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
