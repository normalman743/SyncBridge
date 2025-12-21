from datetime import datetime
from typing import Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Form, User


def get(db: Session, form_id: int) -> Form | None:
    return db.query(Form).filter(Form.id == form_id).first()


def list_for_user(db: Session, user: User, page: int, page_size: int, available_only: bool = False):
    query = db.query(Form)

    if user.role == "client":
        query = query.filter(Form.user_id == user.id)
    elif user.role == "developer":
        if available_only:
            # Developer pulls “open” list when explicitly asking for available_only
            query = query.filter(Form.status == "available")
        else:
            # Developer default view: only forms assigned to self in active/closed states
            query = query.filter(
                Form.developer_id == user.id,
                Form.status.in_(["processing", "rewrite", "end", "error"]),
            )
    else:
        if available_only:
            query = query.filter(Form.status == "available")

    total = query.count()
    items = (
        query.order_by(Form.created_at.desc())
        .offset(max(page - 1, 0) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def create_mainform(db: Session, client_id: int, payload: dict) -> Form:
    now = datetime.utcnow()
    form = Form(
        type="mainform",
        user_id=client_id,
        developer_id=None,
        created_by=client_id,
        title=payload.get("title"),
        message=payload.get("message"),
        budget=payload.get("budget"),
        expected_time=payload.get("expected_time"),
        status="preview",
        created_at=now,
        updated_at=now,
    )
    db.add(form)
    db.commit()
    db.refresh(form)
    return form


def update_form(db: Session, form: Form, changes: dict) -> Form:
    allowed_fields = {
        "title",
        "message",
        "budget",
        "expected_time",
        "status",
        "developer_id",
    }
    for field, value in changes.items():
        if field in allowed_fields and hasattr(form, field):
            setattr(form, field, value)
    form.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


def delete_form(db: Session, form: Form):
    db.delete(form)
    db.commit()


def create_subform(db: Session, mainform: Form, creator_id: int, payload: dict) -> Tuple[Form | None, str | None]:
    if mainform.subform_id is not None:
        return None, "Subform already exists"

    now = datetime.utcnow()
    sub = Form(
        type="subform",
        user_id=mainform.user_id,
        developer_id=mainform.developer_id,
        created_by=creator_id,
        title=payload.get("title"),
        message=payload.get("message"),
        budget=payload.get("budget"),
        expected_time=payload.get("expected_time"),
        status="rewrite",
        created_at=now,
        updated_at=now,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    mainform.subform_id = sub.id
    mainform.status = "rewrite"
    db.commit()

    return sub, None


def merge_subform(db: Session, mainform: Form, subform: Form) -> Form:
    """Merge subform content into mainform, copy functions/nonfunctions with is_changed reset, delete subform, set mainform to processing."""
    from app.models import Function, NonFunction

    # Overwrite mainform fields from subform
    mainform.title = subform.title
    mainform.message = subform.message
    mainform.budget = subform.budget
    mainform.expected_time = subform.expected_time

    # Delete old mainform functions/nonfunctions first
    db.query(Function).filter(Function.form_id == mainform.id).delete()
    db.query(NonFunction).filter(NonFunction.form_id == mainform.id).delete()

    # Copy functions from subform to mainform, resetting is_changed
    subform_functions = db.query(Function).filter(Function.form_id == subform.id).all()
    for sf in subform_functions:
        new_func = Function(
            form_id=mainform.id,
            name=sf.name,
            choice=sf.choice,
            description=sf.description,
            status=sf.status,
            is_changed=0,
        )
        db.add(new_func)

    # Copy nonfunctions from subform to mainform, resetting is_changed
    subform_nonfunctions = db.query(NonFunction).filter(NonFunction.form_id == subform.id).all()
    for snf in subform_nonfunctions:
        new_nf = NonFunction(
            form_id=mainform.id,
            name=snf.name,
            level=snf.level,
            description=snf.description,
            status=snf.status,
            is_changed=0,
        )
        db.add(new_nf)

    # Unlink and delete subform
    mainform.subform_id = None
    mainform.status = "processing"
    mainform.updated_at = datetime.utcnow()
    db.delete(subform)
    db.commit()
    db.refresh(mainform)

    return mainform
