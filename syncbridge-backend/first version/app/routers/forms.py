# app/routers/forms.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, utils, models
from ..permissions import (
    get_current_user, assert_can_view_form, assert_can_create_mainform,
    assert_can_update_mainform, assert_can_update_subform, assert_can_delete_form,
    assert_can_create_subform, validate_status_transition
)
from typing import Optional

router = APIRouter()

@router.get("/forms")
def list_forms(page:int=1, page_size:int=20, available_only:bool=False, current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = crud.list_forms_for_user(db, current, page, page_size, available_only)
    out = []
    for f in items:
        out.append({
            "id": f.id,
            "type": f.type.value,
            "title": f.title,
            "status": f.status.value,
            "subform_id": f.subform_id,
            "created_at": str(f.created_at)
        })
    return utils.success({"forms": out, "page": page, "page_size": page_size, "total": total})

@router.get("/form/{id}")
def get_form(id:int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    f = crud.get_form(db, id)
    if not f:
        raise HTTPException(status_code=404, detail=utils.error("Not found", "NOT_FOUND"))
    assert_can_view_form(f, current)
    data = {
        "id": f.id,
        "type": f.type.value,
        "title": f.title,
        "message": f.message,
        "budget": f.budget,
        "expected_time": f.expected_time,
        "status": f.status.value,
        "user_id": f.user_id,
        "developer_id": f.developer_id,
        "subform_id": f.subform_id,
        "created_at": str(f.created_at),
        "updated_at": str(f.updated_at) if f.updated_at else None
    }
    return utils.success(data)

@router.post("/form")
def create_form(payload: schemas.FormCreate, current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    assert_can_create_mainform(current)
    f = crud.create_mainform(db, current.id, payload.dict())
    return utils.success({"form_id": f.id}, "Form created")

@router.put("/form/{id}")
def update_form(id: int, changes: dict = Body(...), current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = crud.get_form(db, id)
    if not f:
        raise HTTPException(status_code=404, detail=utils.error("Not found", "NOT_FOUND"))
    if f.type == models.FormType.mainform:
        assert_can_update_mainform(f, current)
    else:
        assert_can_update_subform(f, current)
    crud.update_form(db, f, changes)
    return utils.success(None, "Form updated")

@router.delete("/form/{id}")
def delete_form(id:int, current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = crud.get_form(db, id)
    if not f:
        raise HTTPException(status_code=404, detail=utils.error("Not found", "NOT_FOUND"))
    assert_can_delete_form(f, current, db)
    # if deleting subform, unlink mainform
    if f.type == models.FormType.subform:
        main = db.query(models.Form).filter(models.Form.subform_id == f.id).first()
        if main:
            main.subform_id = None
            main.status = models.FormStatus.processing
            db.add(main); db.commit()
    crud.delete_form(db, f)
    return utils.success(None, "Form deleted")

@router.post("/form/{id}/subform")
def create_subform(id:int, payload: schemas.FormCreate, current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    main = crud.get_form(db, id)
    if not main or main.type != models.FormType.mainform:
        raise HTTPException(status_code=400, detail=utils.error("Invalid mainform", "VALIDATION_ERROR"))
    assert_can_create_subform(main, current)
    s, err = crud.create_subform(db, main, current.id, payload.dict())
    if err:
        raise HTTPException(status_code=409, detail=utils.error("Conflict", "CONFLICT"))
    return utils.success({"subform_id": s.id}, "Subform created")

@router.put("/form/{id}/status")
def update_status(id:int, body: dict = Body(...), current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_status = body.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail=utils.error("status required", "VALIDATION_ERROR"))
    f = crud.get_form(db, id)
    if not f:
        raise HTTPException(status_code=404, detail=utils.error("Not found", "NOT_FOUND"))
    # validate transition
    validate_status_transition(f.status, new_status)
    # role-specific permission checks
    if current.role.value == "client":
        # client can set preview -> available or set error on own form
        if f.user_id != current.id:
            raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
        if not (f.status == models.FormStatus.preview and new_status == "available") and new_status != "error":
            raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
    elif current.role.value == "developer":
        # developer taking order: available->processing allowed
        if new_status == "processing" and f.status == models.FormStatus.available:
            f.developer_id = current.id
        else:
            if f.developer_id != current.id:
                raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
    else:
        # admin allowed
        pass
    f.status = models.FormStatus(new_status)
    db.add(f); db.commit(); db.refresh(f)
    return utils.success(None, "Status updated")
