from datetime import datetime
from sqlalchemy.orm import Session

from app.models import NonFunction


def get_by_id(db: Session, nf_id: int) -> NonFunction | None:
    return db.query(NonFunction).filter(NonFunction.id == nf_id).first()


def list_by_form(db: Session, form_id: int):
    return db.query(NonFunction).filter(NonFunction.form_id == form_id).all()


def create(db: Session, payload: dict) -> NonFunction:
    now = datetime.utcnow()
    nf = NonFunction(
        form_id=payload["form_id"],
        name=payload["name"],
        level=payload.get("level"),
        description=payload.get("description"),
        status=payload.get("status", "available"),
        is_changed=payload.get("is_changed", False),
        created_at=now,
        updated_at=now,
    )
    db.add(nf)
    db.commit()
    db.refresh(nf)
    return nf


def update(db: Session, nf: NonFunction, changes: dict) -> NonFunction:
    allowed_fields = {"name", "level", "description", "status", "is_changed"}
    for field, value in changes.items():
        if field in allowed_fields and hasattr(nf, field):
            setattr(nf, field, value)
    nf.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(nf)
    return nf


def delete(db: Session, nf: NonFunction):
    db.delete(nf)
    db.commit()
