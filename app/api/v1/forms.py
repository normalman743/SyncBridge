# app/routers/forms.py
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.api.v1.deps import get_db
from app.models import Form, User
from app.repositories import forms as form_repo
from app.schemas import FormCreate, FormUpdate
from app.services.audit import log_audit
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
    
    # Capture old values for audit
    old_data = {k: getattr(f, k, None) for k in changes.keys()}
    
    form_repo.update_form(db, f, changes)
    
    # Audit log
    log_audit(db, "form", f.id, "update", current.id, old_data, changes)
    
    return success(None, "Form updated")

@router.delete("/form/{id}")
def delete_form(id: int, set_error: bool = False, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = form_repo.get(db, id)
    if not f:
        raise HTTPException(status_code=404, detail=error("Not found", "NOT_FOUND"))
    assert_can_delete_form(f, current, db)
    # if deleting subform, unlink mainform
    if f.type == "subform":
        main = db.query(Form).filter(Form.subform_id == f.id).first()
        if main:
            main.subform_id = None
            # set_error param allows setting mainform to error on negotiation failure
            main.status = "error" if set_error else "processing"
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

@router.post("/form/{mainform_id}/subform/merge")
def merge_subform(mainform_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mainform = form_repo.get(db, mainform_id)
    if not mainform or mainform.type != "mainform":
        raise HTTPException(status_code=400, detail=error("Invalid mainform", "VALIDATION_ERROR"))
    if mainform.subform_id is None:
        raise HTTPException(status_code=404, detail=error("No subform to merge", "NOT_FOUND"))
    subform = form_repo.get(db, mainform.subform_id)
    if not subform:
        raise HTTPException(status_code=404, detail=error("Subform not found", "NOT_FOUND"))
    # Permission: client can merge if they own the form
    if current.role == "client":
        if mainform.user_id != current.id:
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    elif current.role == "developer":
        # Developer can merge if they're bound to the mainform
        if mainform.developer_id != current.id:
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    else:
        raise HTTPException(status_code=403, detail=error("Only client or developer can merge", "FORBIDDEN"))
    
    subform_id = mainform.subform_id
    form_repo.merge_subform(db, mainform, subform)
    
    # Audit log
    log_audit(db, "form", mainform.id, "merge_subform", current.id, {"subform_id": subform_id}, {"merged": True})
    
    return success(None, "Subform merged")

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
        # client can set preview -> available or标记协商失败为 error（需是自己的单）
        if f.user_id != current.id:
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
        if (f.status, new_status) == ("preview", "available"):
            pass
        elif new_status == "error" and f.status in ("processing", "rewrite"):
            pass
        else:
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    elif current.role == "developer":
        # developer taking order: available->processing allowed
        if new_status == "processing" and f.status == "available":
            f.developer_id = current.id
        else:
            # developer bound to form can: processing→{rewrite,end,error}, rewrite→{processing,error}
            if f.developer_id != current.id:
                raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
            valid_developer_transitions = [
                ("processing", "rewrite"),
                ("processing", "end"),
                ("processing", "error"),
                ("rewrite", "processing"),
                ("rewrite", "end"),
                ("rewrite", "error"),
            ]
            if (f.status, new_status) not in valid_developer_transitions:
                raise HTTPException(status_code=403, detail=error("Developer cannot perform this transition", "FORBIDDEN"))
    else:
        raise HTTPException(status_code=403, detail=error("Only client or developer can update status", "FORBIDDEN"))
    old_status = f.status
    f.status = new_status
    db.add(f); db.commit(); db.refresh(f)
    
    # Audit log (isolated, failure won't break response)
    log_audit(db, "form", f.id, "status_change", current.id, {"status": old_status}, {"status": new_status})
    
    return success(None, "Status updated")
