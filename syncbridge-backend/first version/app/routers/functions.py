# app/routers/functions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, utils, models
from ..permissions import get_current_user, assert_can_add_function_to_form, assert_can_edit_function
from typing import List

router = APIRouter()

@router.get("/functions")
def list_functions(form_id:int, current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # permission: ensure current can view the parent form first
    form = crud.get_form(db, form_id)
    if not form:
        raise HTTPException(status_code=404, detail=utils.error("Form not found", "NOT_FOUND"))
    # reuse view rules
    # view permission check
    try:
        from ..permissions import assert_can_view_form
        assert_can_view_form(form, current)
    except HTTPException as e:
        raise e
    funcs = crud.list_functions(db, form_id)
    out = [{"id":f.id,"form_id":f.form_id,"name":f.name,"choice":f.choice.value if f.choice else None,"description":f.description,"status":f.status.value,"is_changed":f.is_changed} for f in funcs]
    return utils.success({"functions": out})

@router.post("/function")
def create_function(payload: schemas.FunctionIn, current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    form = crud.get_form(db, payload.form_id)
    if not form:
        raise HTTPException(status_code=404, detail=utils.error("Form not found", "NOT_FOUND"))
    assert_can_add_function_to_form(form, current)
    f = crud.create_function(db, payload.dict())
    return utils.success({"id": f.id}, "Function created")

@router.put("/function/{id}")
def update_function(id: int, changes: dict = Body(...), current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    fn = db.query(models.Function).filter(models.Function.id==id).first()
    if not fn:
        raise HTTPException(status_code=404, detail=utils.error("Function not found","NOT_FOUND"))
    assert_can_edit_function(fn, current, db)
    # apply changes
    for k,v in changes.items():
        if hasattr(fn, k):
            setattr(fn, k, v)
    db.add(fn); db.commit(); db.refresh(fn)
    return utils.success(None, "Function updated")

@router.delete("/function/{id}")
def delete_function(id:int, current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    fn = db.query(models.Function).filter(models.Function.id==id).first()
    if not fn:
        raise HTTPException(status_code=404, detail=utils.error("Function not found","NOT_FOUND"))
    assert_can_edit_function(fn, current, db)
    db.delete(fn); db.commit()
    return utils.success(None, "Function deleted")
