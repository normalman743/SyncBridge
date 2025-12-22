from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models import Block, File, Form, Message, Function, NonFunction, User
from app.repositories import users as user_repo, forms as form_repo
from app.utils import decode_token, error

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail=error("Invalid token", "UNAUTHORIZED"))
    uid = payload.get("sub")
    if uid is None:
        raise HTTPException(status_code=401, detail=error("Invalid token payload", "UNAUTHORIZED"))
    user = user_repo.get_by_id(db, int(uid))
    if not user:
        raise HTTPException(status_code=401, detail=error("User not found", "UNAUTHORIZED"))
    return user


def require_role(user: User, role: str):
    if user.role is None or user.role != role:
        raise HTTPException(status_code=403, detail=error("Forbidden: insufficient role", "FORBIDDEN"))


# ---------- Form access rules ----------

def assert_can_view_form(form: Form, current: User):
    if current.role is None:
        raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))

    if current.role == "client":
        if form.user_id != current.id and form.created_by != current.id:
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    elif current.role == "developer":
        if form.type == "mainform":
            if form.status != "available" and form.developer_id != current.id:
                raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
        else:
            if form.created_by != current.id and form.developer_id != current.id:
                raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    else:
        raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))


def assert_can_create_mainform(current: User):
    if current.role is None or current.role != "client":
        raise HTTPException(status_code=403, detail=error("Only client can create mainform", "FORBIDDEN"))


def assert_can_update_mainform(form: Form, current: User):
    if form.type != "mainform":
        raise HTTPException(status_code=403, detail=error("Not a mainform", "FORBIDDEN"))

    if current.role == "client":
        if form.user_id != current.id:
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
        if form.status not in ("preview", "available"):
            raise HTTPException(status_code=409, detail=error("Status not allow edit", "CONFLICT"))
    elif current.role == "developer":
        if form.developer_id != current.id:
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
        if form.status not in ("processing", "rewrite"):
            raise HTTPException(status_code=409, detail=error("Status not allow edit", "CONFLICT"))
    else:
        raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))


def assert_can_update_subform(form: Form, current: User):
    if form.type != "subform":
        raise HTTPException(status_code=403, detail=error("Not a subform", "FORBIDDEN"))
    if form.created_by != current.id:
        raise HTTPException(status_code=403, detail=error("Only creator can modify subform", "FORBIDDEN"))


def assert_can_delete_form(form: Form, current: User, db: Session):
    if form.type == "mainform":
        if current.role != "client" or form.user_id != current.id:
            raise HTTPException(status_code=403, detail=error("Cannot delete mainform", "FORBIDDEN"))
        if form.status != "preview":
            raise HTTPException(status_code=409, detail=error("Mainform can be deleted only in preview", "CONFLICT"))
    else:
        if form.created_by != current.id:
            raise HTTPException(status_code=403, detail=error("Cannot delete subform", "FORBIDDEN"))


def assert_can_create_subform(mainform: Form, current: User):
    if mainform.type != "mainform":
        raise HTTPException(status_code=400, detail=error("Invalid mainform", "VALIDATION_ERROR"))
    if mainform.subform_id is not None:
        raise HTTPException(status_code=409, detail=error("Subform exists", "CONFLICT"))
    if mainform.status not in ("available", "processing", "rewrite"):
        raise HTTPException(status_code=409, detail=error("Status not allow subform", "CONFLICT"))
    # Enforce role-based binding: developer must be bound to mainform
    if current.role == "developer":
        if mainform.developer_id != current.id:
            raise HTTPException(status_code=403, detail=error("Developer not bound to this mainform", "FORBIDDEN"))


# ---------- Function / NonFunction permissions ----------

def assert_can_add_function_to_form(form: Form, current: User):
    if form.type == "mainform":
        if current.role == "client" and form.user_id != current.id:
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
        if current.role == "developer" and form.developer_id != current.id and form.status != "available":
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    else:
        if form.created_by != current.id:
            raise HTTPException(status_code=403, detail=error("Only subform creator can add functions", "FORBIDDEN"))


def assert_can_edit_function(fn: Function | NonFunction, current: User, db: Session):
    form = form_repo.get(db, fn.form_id)
    if not form:
        raise HTTPException(status_code=404, detail=error("Form not found", "NOT_FOUND"))
    if form.type == "mainform":
        if current.role == "client":
            if form.user_id != current.id:
                raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
            if form.status not in ("preview", "available"):
                raise HTTPException(status_code=409, detail=error("Status not allow edit", "CONFLICT"))
        elif current.role == "developer":
            if form.developer_id != current.id:
                raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    else:
        if form.created_by != current.id:
            raise HTTPException(status_code=403, detail=error("Only subform creator can edit its functions", "FORBIDDEN"))


# ---------- Messages & Blocks ----------

def assert_can_access_block(form: Form, current: User, db: Session):
    if current.role == "client":
        if form.user_id != current.id:
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    elif current.role == "developer":
        if form.developer_id != current.id and form.status != "available":
            raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    else:
        raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))


def assert_can_post_message(form: Form, current: User):
    if current.role == "client" and form.user_id != current.id:
        raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))
    if current.role == "developer" and form.developer_id != current.id and form.status != "available":
        raise HTTPException(status_code=403, detail=error("Forbidden", "FORBIDDEN"))


def assert_can_edit_message(msg: Message, current: User):
    if msg.user_id != current.id:
        raise HTTPException(status_code=403, detail=error("Only sender can modify message", "FORBIDDEN"))


# ---------- Files ----------

def assert_can_upload_file(message: Message, current: User, db: Session):
    block = db.query(Block).filter(Block.id == message.block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail=error("Block not found", "NOT_FOUND"))
    form = db.query(Form).filter(Form.id == block.form_id).first()
    assert_can_access_block(form, current, db)
    return True


def assert_can_delete_file(file_rec: File, current: User, db: Session):
    msg = db.query(Message).filter(Message.id == file_rec.message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail=error("Message not found", "NOT_FOUND"))
    if msg.user_id != current.id:
        raise HTTPException(status_code=403, detail=error("Only sender can delete file", "FORBIDDEN"))


# ---------- Status transition validator ----------

def validate_status_transition(old_status: str, new_status: str):
    valid = {
        "preview": ["available"],  # client
        "available": ["processing"],  # developer
        "processing": ["rewrite", "end"],  # developer or client → rewrite; developer and client → end
        "rewrite": ["processing", "error"],  # developer and client → processing; developer or client → error
        "end": [],    # terminal
        "error": [],  # terminal
    }
    if old_status not in valid or new_status not in valid[old_status]:
        raise HTTPException(status_code=409, detail=error("Invalid status transition", "CONFLICT"))
