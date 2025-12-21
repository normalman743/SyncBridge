from datetime import datetime
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models import User
from app.repositories import licenses as license_repo
from app.repositories import users as user_repo
from app.schemas import LoginIn, ReactivateIn, RegisterIn
from app.utils import create_access_token, error, success
from app.services.permissions import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


# ============================
#  注册 Register
# ============================
@router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):

    if user_repo.get_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail=error("Email exists", "CONFLICT"))

    # 简单口令强度：>=8 且含字母和数字
    if len(payload.password) < 8 or not re.search(r"[A-Za-z]", payload.password) or not re.search(r"\d", payload.password):
        raise HTTPException(status_code=400, detail=error("Password too weak (need >=8 chars with letters and digits)", "VALIDATION_ERROR"))

    user = user_repo.create(db, payload.email, payload.password, payload.display_name)

    license_row, err = license_repo.activate(db, payload.license_key, user)
    if err:
        db.delete(user)
        db.commit()
        raise HTTPException(status_code=403, detail=error("License invalid or not available", "FORBIDDEN"))

    token = create_access_token({"sub": user.id, "role": user.role})

    return success(
        {
            "user_id": user.id,
            "role": user.role,
            "access_token": token,
            "license_status": license_row.status,
            "license_expires_at": license_row.expires_at,
        },
        "User registered and activated",
    )


# ============================
#   登录 Login
# ============================
@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):

    user = user_repo.authenticate(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail=error("Invalid credentials", "UNAUTHORIZED"))

    # 用户被停用则直接阻断
    if user.is_active == 0:
        raise HTTPException(status_code=403, detail=error("User is inactive", "FORBIDDEN"))

    lic, err = license_repo.validate_active(db, user)
    if err:
        user.is_active = 0
        user.updated_at = datetime.utcnow()
        db.add(user); db.commit(); db.refresh(user)
        # 细分错误文案，仍使用 FORBIDDEN 代码
        msg = "License invalid or expired"
        if "expired" in err.lower():
            msg = "License expired"
        elif "not active" in err.lower():
            msg = "License not active"
        elif "not found" in err.lower():
            msg = "License not found"
        raise HTTPException(status_code=403, detail=error(msg, "FORBIDDEN"))

    token = create_access_token({"sub": user.id, "role": user.role, "license_status": lic.status})

    return success(
        {
            "access_token": token,
            "role": user.role,
            "license_status": lic.status,
            "license_expires_at": lic.expires_at,
        },
        "Login success",
    )


# ============================
#     /me 获取用户信息
# ============================
@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return success(
        {
            "user_id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "role": current_user.role,
        },
        "OK"
    )


# ============================
#   重新激活 Reactivate with new license
# ============================
@router.post("/reactivate")
def reactivate(payload: ReactivateIn, db: Session = Depends(get_db)):
    user = user_repo.authenticate(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail=error("Invalid credentials", "UNAUTHORIZED"))

    lic, err = license_repo.activate_new_for_user(db, payload.license_key, user)
    if err:
        raise HTTPException(status_code=403, detail=error(err, "FORBIDDEN"))

    token = create_access_token({"sub": user.id, "role": user.role})

    return success(
        {
            "user_id": user.id,
            "role": user.role,
            "access_token": token,
        },
        "User reactivated",
    )
