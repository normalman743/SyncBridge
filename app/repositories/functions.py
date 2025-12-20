from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Function


def get_by_id(db: Session, function_id: int) -> Function | None:
    return db.query(Function).filter(Function.id == function_id).first()


def list_by_form(db: Session, form_id: int):
    return db.query(Function).filter(Function.form_id == form_id).all()


def create(db: Session, payload: dict) -> Function:
    now = datetime.utcnow()
    fn = Function(
        form_id=payload["form_id"],
        name=payload["name"],
        choice=payload.get("choice"),
        description=payload.get("description"),
        status=payload.get("status", "available"),
        is_changed=payload.get("is_changed", False),
        created_at=now,
        updated_at=now,
    )
    db.add(fn)
    db.commit()
    db.refresh(fn)
    return fn


def update(db: Session, fn: Function, changes: dict) -> Function:
    for field, value in changes.items():
        if hasattr(fn, field):
            setattr(fn, field, value)
    fn.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(fn)
    return fn


def delete(db: Session, fn: Function):
    db.delete(fn)
    db.commit()
