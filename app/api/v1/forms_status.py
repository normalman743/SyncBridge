# Status transition helper for forms requiring both parties' agreement
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_db
from app.models import User
from app.repositories import forms as form_repo
from app.services.audit import log_audit
from app.utils import error, success

router = APIRouter()


@router.post("/form/{id}/complete")
def complete_form(id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Mark form as completed (processing → end).
    Requires explicit confirmation endpoint to ensure both parties agree.
    Client initiates; developer must have already marked as ready.
    """
    f = form_repo.get(db, id)
    if not f:
        raise HTTPException(status_code=404, detail=error("Form not found", "NOT_FOUND"))
    
    if f.status != "processing":
        raise HTTPException(status_code=409, detail=error("Can only complete forms in processing", "CONFLICT"))
    
    # Only client can mark as complete (after developer signals readiness)
    if current.role != "client" or f.user_id != current.id:
        raise HTTPException(status_code=403, detail=error("Only form owner can mark complete", "FORBIDDEN"))
    
    if not f.developer_id:
        raise HTTPException(status_code=409, detail=error("No developer assigned", "CONFLICT"))
    
    old_status = f.status
    f.status = "end"
    db.add(f)
    db.commit()
    db.refresh(f)
    
    log_audit(db, "form", f.id, "complete", current.id, {"status": old_status}, {"status": "end"})
    
    return success(None, "Form marked as completed")


@router.post("/form/{id}/accept-negotiation")
def accept_negotiation(id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Accept negotiation result (rewrite → processing).
    Requires both parties to have agreed on subform merge before calling this.
    Should be called after POST /form/{mainform_id}/subform/merge.
    """
    f = form_repo.get(db, id)
    if not f:
        raise HTTPException(status_code=404, detail=error("Form not found", "NOT_FOUND"))
    
    if f.status != "rewrite":
        raise HTTPException(status_code=409, detail=error("Form not in rewrite state", "CONFLICT"))
    
    # Verify caller is involved party
    is_client = current.role == "client" and f.user_id == current.id
    is_developer = current.role == "developer" and f.developer_id == current.id
    
    if not (is_client or is_developer):
        raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    
    # Ensure subform has been merged (no active subform)
    if f.subform_id is not None:
        raise HTTPException(status_code=409, detail=error("Subform must be merged before accepting", "CONFLICT"))
    
    old_status = f.status
    f.status = "processing"
    db.add(f)
    db.commit()
    db.refresh(f)
    
    log_audit(db, "form", f.id, "accept_negotiation", current.id, {"status": old_status}, {"status": "processing"})
    
    return success(None, "Negotiation accepted, returning to processing")
