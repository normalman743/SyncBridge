from sqlalchemy.orm import Session
from datetime import datetime
from .models import User, License, Form, Function, NonFunction, Block, Message, File
from .utils import get_password_hash, verify_password


# ======================================================
#                   User & License
# ======================================================

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, email: str, password: str, display_name: str):
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        display_name=display_name,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# ----------------- License Activate -------------------

def get_license(db: Session, key: str):
    return db.query(License).filter(License.license_key == key).first()


def activate_license(db: Session, license_key: str, user: User):
    """
    Return: (license_row, err_message)
    err_message = None  → success
    """
    lic = get_license(db, license_key)
    if not lic:
        return None, "License not found"

    if lic.status != "unused":
        return None, "License not unused"

    # Bind license
    lic.status = "active"
    lic.user_id = user.id
    lic.activated_at = datetime.utcnow()

    # Set user role
    user.role = lic.role
    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)
    db.refresh(lic)
    return lic, None


# ======================================================
#                   Forms (Main/Sub)
# ======================================================

def get_form(db: Session, form_id: int):
    return db.query(Form).filter(Form.id == form_id).first()


def create_mainform(db: Session, user: User, payload):
    form = Form(
        type="mainform",
        user_id=user.id,
        created_by=user.id,
        title=payload.title,
        message=payload.message,
        budget=payload.budget,
        expected_time=payload.expected_time,
        status="preview",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(form)
    db.commit()
    db.refresh(form)
    return form


def update_form(db: Session, form: Form, payload):
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(form, field, value)
    form.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


def delete_form(db: Session, form: Form):
    db.delete(form)
    db.commit()


# ---------------- Subform ----------------

def create_subform(db: Session, mainform: Form, user: User, payload):
    sub = Form(
        type="subform",
        user_id=mainform.user_id,
        developer_id=mainform.developer_id,
        created_by=user.id,
        title=payload.title,
        message=payload.message,
        budget=payload.budget,
        expected_time=payload.expected_time,
        status="rewrite",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    mainform.subform_id = sub.id
    mainform.status = "rewrite"
    db.commit()

    return sub


# ======================================================
#               Functions & NonFunctions
# ======================================================

def get_functions_by_form(db: Session, form_id: int):
    return db.query(Function).filter(Function.form_id == form_id).all()


def create_function(db: Session, form_id: int, payload):
    fn = Function(
        form_id=form_id,
        name=payload.name,
        choice=payload.choice,
        description=payload.description,
        status=payload.status,
        is_changed=payload.is_changed,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(fn)
    db.commit()
    db.refresh(fn)
    return fn


def update_function(db: Session, fn: Function, payload):
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(fn, field, value)
    fn.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(fn)
    return fn


def delete_function(db: Session, fn: Function):
    db.delete(fn)
    db.commit()


# --------- NonFunctions ---------

def get_nonfunctions_by_form(db: Session, form_id: int):
    return db.query(NonFunction).filter(NonFunction.form_id == form_id).all()


def create_nonfunction(db: Session, form_id: int, payload):
    nf = NonFunction(
        form_id=form_id,
        name=payload.name,
        level=payload.level,
        description=payload.description,
        status=payload.status,
        is_changed=payload.is_changed,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(nf)
    db.commit()
    db.refresh(nf)
    return nf


def update_nonfunction(db: Session, nf: NonFunction, payload):
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(nf, field, value)
    nf.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(nf)
    return nf


def delete_nonfunction(db: Session, nf: NonFunction):
    db.delete(nf)
    db.commit()


# ======================================================
#                   Messages & Blocks
# ======================================================

def get_or_create_block(db: Session, form_id: int, block_type: str, target_id=None):
    """
    block_type: general / function / nonfunction
    """
    q = db.query(Block).filter(
        Block.form_id == form_id,
        Block.type == block_type,
        Block.target_id == target_id
    )
    block = q.first()
    if block:
        return block

    block = Block(
        form_id=form_id,
        type=block_type,
        target_id=target_id,
        status="normal",
        created_at=datetime.utcnow()
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


def create_message(db: Session, block_id: int, user_id: int, text: str):
    msg = Message(
        block_id=block_id,
        user_id=user_id,
        text_content=text,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def update_message(db: Session, msg: Message, text: str):
    msg.text_content = text
    msg.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(msg)
    return msg


def delete_message(db: Session, msg: Message):
    db.delete(msg)
    db.commit()


# ======================================================
#                        Files
# ======================================================

def create_file(db: Session, message_id: int, filename: str, file_type: str, file_size: int, storage_path: str):
    f = File(
        message_id=message_id,
        file_name=filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=storage_path,
        created_at=datetime.utcnow()
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def delete_file(db: Session, f: File):
    db.delete(f)
    db.commit()
