# app/routers/nonfunctions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models import NonFunction, User
from app.repositories import forms as form_repo
from app.repositories import nonfunctions as nonfunction_repo
from app.schemas import NonFunctionIn, NonFunctionUpdate
from app.services.permissions import assert_can_add_function_to_form, assert_can_edit_function, assert_can_view_form, get_current_user
from app.utils import error, success

# Note: functions permission helpers are reused because rules are identical
router = APIRouter()

@router.get("/nonfunctions")
def list_nonfunctions(form_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    form = form_repo.get(db, form_id)
    if not form:
        raise HTTPException(status_code=404, detail=error("Form not found", "NOT_FOUND"))
    assert_can_view_form(form, current)
    items = nonfunction_repo.list_by_form(db, form_id)
    out = [
        {
            "id": i.id,
            "form_id": i.form_id,
            "name": i.name,
            "level": i.level,
            "description": i.description,
            "status": i.status,
            "is_changed": i.is_changed,
        }
        for i in items
    ]
    return success({"nonfunctions": out})

@router.post("/nonfunction")
def create_nonfunction(payload: NonFunctionIn, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    form = form_repo.get(db, payload.form_id)
    if not form:
        raise HTTPException(status_code=404, detail=error("Form not found", "NOT_FOUND"))
    assert_can_add_function_to_form(form, current)
    nf = nonfunction_repo.create(db, payload.dict())
    return success({"id": nf.id}, "NonFunction created")

@router.put("/nonfunction/{id}")
def update_nonfunction(id: int, payload: NonFunctionUpdate, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    nf = nonfunction_repo.get_by_id(db, id)
    if not nf:
        raise HTTPException(status_code=404, detail=error("NonFunction not found", "NOT_FOUND"))
    assert_can_edit_function(nf, current, db)
    changes = payload.dict(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail=error("No valid fields to update", "VALIDATION_ERROR"))
    nonfunction_repo.update(db, nf, changes)
    return success(None, "NonFunction updated")

@router.delete("/nonfunction/{id}")
def delete_nonfunction(id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    nf = nonfunction_repo.get_by_id(db, id)
    if not nf:
        raise HTTPException(status_code=404, detail=error("NonFunction not found", "NOT_FOUND"))
    assert_can_edit_function(nf, current, db)
    nonfunction_repo.delete(db, nf)
    return success(None, "NonFunction deleted")
