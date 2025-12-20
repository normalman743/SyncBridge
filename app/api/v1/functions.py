# app/routers/functions.py
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.v1.deps import get_db
from app.models import Function, User
from app.repositories import forms as form_repo
from app.repositories import functions as function_repo
from app.schemas import FunctionIn
from app.services.permissions import assert_can_add_function_to_form, assert_can_edit_function, assert_can_view_form, get_current_user
from app.utils import error, success

router = APIRouter()

@router.get("/functions")
def list_functions(form_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # permission: ensure current can view the parent form first
    form = form_repo.get(db, form_id)
    if not form:
        raise HTTPException(status_code=404, detail=error("Form not found", "NOT_FOUND"))
    # reuse view rules
    # view permission check
    assert_can_view_form(form, current)
    funcs = function_repo.list_by_form(db, form_id)
    out = [
        {
            "id": f.id,
            "form_id": f.form_id,
            "name": f.name,
            "choice": f.choice,
            "description": f.description,
            "status": f.status,
            "is_changed": f.is_changed,
        }
        for f in funcs
    ]
    return success({"functions": out})

@router.post("/function")
def create_function(payload: FunctionIn, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    form = form_repo.get(db, payload.form_id)
    if not form:
        raise HTTPException(status_code=404, detail=error("Form not found", "NOT_FOUND"))
    assert_can_add_function_to_form(form, current)
    f = function_repo.create(db, payload.dict())
    return success({"id": f.id}, "Function created")

@router.put("/function/{id}")
def update_function(id: int, changes: dict = Body(...), current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fn = function_repo.get_by_id(db, id)
    if not fn:
        raise HTTPException(status_code=404, detail=error("Function not found", "NOT_FOUND"))
    assert_can_edit_function(fn, current, db)
    function_repo.update(db, fn, changes)
    return success(None, "Function updated")

@router.delete("/function/{id}")
def delete_function(id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fn = function_repo.get_by_id(db, id)
    if not fn:
        raise HTTPException(status_code=404, detail=error("Function not found", "NOT_FOUND"))
    assert_can_edit_function(fn, current, db)
    function_repo.delete(db, fn)
    return success(None, "Function deleted")
