# app/routers/forms.py
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.api.v1.deps import get_db
from app.models import Form, User
from app.repositories import forms as form_repo
from app.schemas import FormCreate, FormUpdate
from app.services.permissions import (
    assert_can_create_mainform,
    assert_can_create_subform,
    assert_can_delete_form,
    assert_can_update_mainform,
    assert_can_update_subform,
    assert_can_view_form,
    get_current_user,
    validate_status_transition,
)
from app.utils import error, success

router = APIRouter()

@router.get("/forms")
def list_forms(page: int = 1, page_size: int = 20, available_only: bool = False, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = form_repo.list_for_user(db, current, page, page_size, available_only)
    out = []
    for f in items:
        out.append({
            "id": f.id,
            "type": f.type,
            "title": f.title,
            "status": f.status,
            "subform_id": f.subform_id,
            "created_at": str(f.created_at)
        })
    return success({"forms": out, "page": page, "page_size": page_size, "total": total})

@router.get("/form/{id}")
def get_form(id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    f = form_repo.get(db, id)
    if not f:
        raise HTTPException(status_code=404, detail=error("Not found", "NOT_FOUND"))
    assert_can_view_form(f, current)
    data = {
        "id": f.id,
        "type": f.type,
        "title": f.title,
        "message": f.message,
        "budget": f.budget,
        "expected_time": f.expected_time,
        "status": f.status,
        "user_id": f.user_id,
        "developer_id": f.developer_id,
        "subform_id": f.subform_id,
        "created_at": str(f.created_at),
        "updated_at": str(f.updated_at) if f.updated_at else None
    }
    return success(data)

@router.post("/form")
def create_form(payload: FormCreate, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    assert_can_create_mainform(current)
    f = form_repo.create_mainform(db, current.id, payload.dict())
    return success({"form_id": f.id}, "Form created")

@router.put("/form/{id}")
def update_form(id: int, payload: FormUpdate, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = form_repo.get(db, id)
    if not f:
        raise HTTPException(status_code=404, detail=error("Not found", "NOT_FOUND"))
    if f.type == "mainform":
        assert_can_update_mainform(f, current)
    else:
        assert_can_update_subform(f, current)
    changes = payload.dict(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail=error("No valid fields to update", "VALIDATION_ERROR"))
    form_repo.update_form(db, f, changes)
    return success(None, "Form updated")

@router.delete("/form/{id}")
def delete_form(id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = form_repo.get(db, id)
    if not f:
        raise HTTPException(status_code=404, detail=error("Not found", "NOT_FOUND"))
    assert_can_delete_form(f, current, db)
    # if deleting subform, unlink mainform
    if f.type == "subform":
        main = db.query(Form).filter(Form.subform_id == f.id).first()
        if main:
            main.subform_id = None
            main.status = "processing"
            db.add(main); db.commit()
    form_repo.delete_form(db, f)
    return success(None, "Form deleted")

@router.post("/form/{id}/subform")
def create_subform(id: int, payload: FormCreate, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    main = form_repo.get(db, id)
    if not main or main.type != "mainform":
        raise HTTPException(status_code=400, detail=error("Invalid mainform", "VALIDATION_ERROR"))
    assert_can_create_subform(main, current)
    s, err = form_repo.create_subform(db, main, current.id, payload.dict())
    if err:
        raise HTTPException(status_code=409, detail=error("Conflict", "CONFLICT"))
    return success({"subform_id": s.id}, "Subform created")

@router.put("/form/{id}/status")
def update_status(id: int, body: dict = Body(...), current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_status = body.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail=error("status required", "VALIDATION_ERROR"))
    f = form_repo.get(db, id)
    if not f:
        raise HTTPException(status_code=404, detail=error("Not found", "NOT_FOUND"))
    # validate transition
    validate_status_transition(f.status, new_status)
    # role-specific permission checks
    if current.role == "client":
        # client can set preview -> available or set error on own form
        if f.user_id != current.id:
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
        if not (f.status == "preview" and new_status == "available") and new_status != "error":
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    elif current.role == "developer":
        # developer taking order: available->processing allowed
        if new_status == "processing" and f.status == "available":
            f.developer_id = current.id
        else:
            if f.developer_id != current.id:
                raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    else:
        # admin allowed
        pass
    f.status = new_status
    db.add(f); db.commit(); db.refresh(f)
    return success(None, "Status updated")
