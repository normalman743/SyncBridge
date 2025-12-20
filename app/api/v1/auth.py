from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models import User
from app.repositories import licenses as license_repo
from app.repositories import users as user_repo
from app.schemas import LoginIn, RegisterIn
from app.utils import create_access_token, decode_access_token, error, success

router = APIRouter(prefix="/auth", tags=["Auth"])


# ============================
#  注册 Register
# ============================
@router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):

    if user_repo.get_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail=error("Email exists", "CONFLICT"))

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

    token = create_access_token({"sub": user.id, "role": user.role})

    return success(
        {
            "access_token": token,
            "role": user.role,
        },
        "Login success",
    )


# ============================
#     从 Header 提取 token
# ============================
def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail=error("Missing token", "UNAUTHORIZED"))

    token = authorization.split(" ")[1].strip()
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail=error("Invalid or expired token", "UNAUTHORIZED"))

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail=error("Invalid token payload", "UNAUTHORIZED"))

    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=error("User not found", "NOT_FOUND"))

    return user


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
