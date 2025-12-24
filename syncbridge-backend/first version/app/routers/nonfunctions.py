# app/routers/nonfunctions.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, utils, models
from ..permissions import get_current_user, assert_can_add_function_to_form, assert_can_edit_function
# Note: functions permission helpers are reused because rules are identical
router = APIRouter()

@router.get("/nonfunctions")
def list_nonfunctions(form_id:int, current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    form = crud.get_form(db, form_id)
    if not form:
        raise HTTPException(status_code=404, detail=utils.error("Form not found", "NOT_FOUND"))
    from ..permissions import assert_can_view_form
    assert_can_view_form(form, current)
    items = db.query(models.NonFunction).filter(models.NonFunction.form_id==form_id).all()
    out = [{"id":i.id,"form_id":i.form_id,"name":i.name,"level":i.level.value if i.level else None,"description":i.description,"status":i.status.value,"is_changed":i.is_changed} for i in items]
    return utils.success({"nonfunctions": out})

@router.post("/nonfunction")
def create_nonfunction(payload: schemas.FunctionIn, current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # reuse same validation as function
    form = crud.get_form(db, payload.form_id)
    if not form:
        raise HTTPException(status_code=404, detail=utils.error("Form not found", "NOT_FOUND"))
    assert_can_add_function_to_form(form, current)
    nf = crud.create_nonfunction(db, payload.dict())
    return utils.success({"id": nf.id}, "NonFunction created")

@router.put("/nonfunction/{id}")
def update_nonfunction(id:int, changes: dict = Body(...), current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    nf = db.query(models.NonFunction).filter(models.NonFunction.id==id).first()
    if not nf:
        raise HTTPException(status_code=404, detail=utils.error("NonFunction not found","NOT_FOUND"))
    # reuse edit check (works same)
    assert_can_edit_function(nf, current, db)
    for k,v in changes.items():
        if hasattr(nf, k):
            setattr(nf, k, v)
    db.add(nf); db.commit(); db.refresh(nf)
    return utils.success(None, "NonFunction updated")

@router.delete("/nonfunction/{id}")
def delete_nonfunction(id:int, current: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    nf = db.query(models.NonFunction).filter(models.NonFunction.id==id).first()
    if not nf:
        raise HTTPException(status_code=404, detail=utils.error("NonFunction not found","NOT_FOUND"))
    assert_can_edit_function(nf, current, db)
    db.delete(nf); db.commit()
    return utils.success(None, "NonFunction deleted")
