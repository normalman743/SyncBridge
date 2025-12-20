# app/permissions.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from . import utils, crud, models
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """
    Decode token and return User model. Raises 401 if invalid.
    """
    payload = utils.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail=utils.error("Invalid token", "UNAUTHORIZED"))
    uid = payload.get("sub")
    if uid is None:
        raise HTTPException(status_code=401, detail=utils.error("Invalid token payload", "UNAUTHORIZED"))
    user = crud.get_user(db, int(uid))
    if not user:
        raise HTTPException(status_code=401, detail=utils.error("User not found", "UNAUTHORIZED"))
    return user

# Role helper
def require_role(user: models.User, role: str):
    if user.role is None or user.role.value != role:
        raise HTTPException(status_code=403, detail=utils.error("Forbidden: insufficient role", "FORBIDDEN"))

# ---------- Form access rules ----------
def assert_can_view_form(form: models.Form, current: models.User):
    """
    View rules:
    - client: can view their own mainform and its subform(s)
    - developer: can view mainform if status == available OR forms assigned to them (developer_id)
      and can view subform if they are assigned to the related mainform or created_by (developer)
    """
    if current.role is None:
        raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))

    if current.role.value == "client":
        # Clients can only view their own mainform/subform
        if form.user_id != current.id and form.created_by != current.id:
            raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
    elif current.role.value == "developer":
        # Developers can view available mainforms (to take) or assigned ones
        if form.type == models.FormType.mainform:
            if form.status != models.FormStatus.available and form.developer_id != current.id:
                raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
        else:
            # subform: allow if developer is assigned to mainform OR created_by is the developer
            parent = None
            # try to find parent mainform: crud.get_form won't find parent by subform id, so rely on db relationships
            # We'll allow if form.created_by==current.id or form.developer_id==current.id
            if form.created_by != current.id and form.developer_id != current.id:
                raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
    else:
        # admin allowed
        return

def assert_can_create_mainform(current: models.User):
    if current.role is None or current.role.value != "client":
        raise HTTPException(status_code=403, detail=utils.error("Only client can create mainform", "FORBIDDEN"))

def assert_can_update_mainform(form: models.Form, current: models.User):
    """
    Update rules for mainform:
    - client: only own mainform and only when status in {preview, available}
    - developer: only assigned developer and only when status in {processing, rewrite}
    """
    if form.type != models.FormType.mainform:
        raise HTTPException(status_code=403, detail=utils.error("Not a mainform", "FORBIDDEN"))

    if current.role.value == "client":
        if form.user_id != current.id:
            raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
        if form.status not in (models.FormStatus.preview, models.FormStatus.available):
            raise HTTPException(status_code=409, detail=utils.error("Status not allow edit", "CONFLICT"))
    elif current.role.value == "developer":
        if form.developer_id != current.id:
            raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
        if form.status not in (models.FormStatus.processing, models.FormStatus.rewrite):
            raise HTTPException(status_code=409, detail=utils.error("Status not allow edit", "CONFLICT"))
    else:
        # admin allowed
        return

def assert_can_update_subform(form: models.Form, current: models.User):
    """
    Update rules for subform: only created_by or admin
    """
    if form.type != models.FormType.subform:
        raise HTTPException(status_code=403, detail=utils.error("Not a subform", "FORBIDDEN"))
    if form.created_by != current.id and (current.role is None or current.role.value != "admin"):
        raise HTTPException(status_code=403, detail=utils.error("Only creator can modify subform", "FORBIDDEN"))

def assert_can_delete_form(form: models.Form, current: models.User, db: Session):
    """
    Delete rules:
    - delete mainform: only client, own mainform, status == preview
    - delete subform: only created_by (or admin)
    """
    if form.type == models.FormType.mainform:
        if current.role.value != "client" or form.user_id != current.id:
            raise HTTPException(status_code=403, detail=utils.error("Cannot delete mainform", "FORBIDDEN"))
        if form.status != models.FormStatus.preview:
            raise HTTPException(status_code=409, detail=utils.error("Mainform can be deleted only in preview", "CONFLICT"))
    else:
        if form.created_by != current.id and (current.role is None or current.role.value != "admin"):
            raise HTTPException(status_code=403, detail=utils.error("Cannot delete subform", "FORBIDDEN"))

def assert_can_create_subform(mainform: models.Form, current: models.User):
    """
    Preconditions to create subform:
    - must be mainform
    - subform_id is NULL
    - status in allowed set
    """
    if mainform.type != models.FormType.mainform:
        raise HTTPException(status_code=400, detail=utils.error("Invalid mainform", "VALIDATION_ERROR"))
    if mainform.subform_id is not None:
        raise HTTPException(status_code=409, detail=utils.error("Subform exists", "CONFLICT"))
    if mainform.status not in (models.FormStatus.available, models.FormStatus.processing, models.FormStatus.rewrite):
        raise HTTPException(status_code=409, detail=utils.error("Status not allow subform", "CONFLICT"))

# ---------- Function / NonFunction permissions ----------
def assert_can_add_function_to_form(form: models.Form, current: models.User):
    """
    mainform: client & assigned developer may add (client only on own form)
    subform: only subform.created_by may add
    """
    if form.type == models.FormType.mainform:
        if current.role.value == "client" and form.user_id != current.id:
            raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
        if current.role.value == "developer" and form.developer_id != current.id and form.status != models.FormStatus.available:
            raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
    else:
        if form.created_by != current.id and (current.role is None or current.role.value != "admin"):
            raise HTTPException(status_code=403, detail=utils.error("Only subform creator can add functions", "FORBIDDEN"))

def assert_can_edit_function(fn: models.Function, current: models.User, db: Session):
    """
    Edit rules for a function:
    - If belongs to mainform: client (owner) & assigned developer allowed (with status checks)
    - If belongs to subform: only subform.created_by
    """
    form = db.query(models.Form).filter(models.Form.id == fn.form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail=utils.error("Form not found", "NOT_FOUND"))
    if form.type == models.FormType.mainform:
        if current.role.value == "client":
            if form.user_id != current.id:
                raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
            if form.status not in (models.FormStatus.preview, models.FormStatus.available):
                raise HTTPException(status_code=409, detail=utils.error("Status not allow edit", "CONFLICT"))
        elif current.role.value == "developer":
            if form.developer_id != current.id:
                raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
    else:
        if form.created_by != current.id and (current.role is None or current.role.value != "admin"):
            raise HTTPException(status_code=403, detail=utils.error("Only subform creator can edit its functions", "FORBIDDEN"))

# ---------- Messages & Blocks ----------
def assert_can_access_block(form: models.Form, current: models.User, db: Session):
    """
    Access rules for block/form:
    - client: owner
    - developer: assigned OR available mainform
    """
    if current.role.value == "client":
        if form.user_id != current.id:
            raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
    elif current.role.value == "developer":
        if form.developer_id != current.id and form.status != models.FormStatus.available:
            raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
    else:
        return

def assert_can_post_message(form: models.Form, current: models.User):
    # reuse access logic: (caller should call assert_can_access_block first)
    if current.role.value == "client" and form.user_id != current.id:
        raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))
    if current.role.value == "developer" and form.developer_id != current.id and form.status != models.FormStatus.available:
        raise HTTPException(status_code=403, detail=utils.error("Forbidden", "FORBIDDEN"))

def assert_can_edit_message(msg: models.Message, current: models.User):
    if msg.user_id != current.id and (current.role is None or current.role.value != "admin"):
        raise HTTPException(status_code=403, detail=utils.error("Only sender or admin can modify message", "FORBIDDEN"))

# ---------- Files ----------
def assert_can_upload_file(message: models.Message, current: models.User, db: Session):
    # check block -> form -> access
    block = db.query(models.Block).filter(models.Block.id == message.block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail=utils.error("Block not found", "NOT_FOUND"))
    form = db.query(models.Form).filter(models.Form.id == block.form_id).first()
    assert_can_access_block(form, current, db)
    return True

def assert_can_delete_file(file_rec: models.File, current: models.User, db: Session):
    msg = db.query(models.Message).filter(models.Message.id == file_rec.message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail=utils.error("Message not found", "NOT_FOUND"))
    if msg.user_id != current.id and (current.role is None or current.role.value != "admin"):
        raise HTTPException(status_code=403, detail=utils.error("Only sender or admin can delete file", "FORBIDDEN"))

# ---------- Status transition validator ----------
def validate_status_transition(old_status: models.FormStatus, new_status: str):
    valid = {
        models.FormStatus.preview.value: ["available"],
        models.FormStatus.available.value: ["processing"],
        models.FormStatus.processing.value: ["rewrite", "end", "error"],
        models.FormStatus.rewrite.value: ["processing", "error"],
        models.FormStatus.end.value: [],
        models.FormStatus.error.value: []
    }
    if old_status.value not in valid or new_status not in valid[old_status.value]:
        raise HTTPException(status_code=409, detail=utils.error("Invalid status transition", "CONFLICT"))
