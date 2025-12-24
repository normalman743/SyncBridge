from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from .. import crud, schemas, utils
from ..database import get_db
from ..models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


# ============================
#  注册 Register
# ============================
@router.post("/register")
def register(payload: schemas.RegisterIn, db: Session = Depends(get_db)):

    # Email 不能重复
    if crud.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail=utils.error("Email exists", "CONFLICT"))

    # 创建用户（注意：role 暂时为空，license 激活后赋值）
    user = crud.create_user(db, payload.email, payload.password, payload.display_name)

    # 激活 license
    license_row, err = crud.activate_license(db, payload.license_key, user)
    if err:
        # rollback: 删除刚创建用户
        db.delete(user)
        db.commit()
        raise HTTPException(status_code=403, detail=utils.error("License invalid or not available", "FORBIDDEN"))

    # 创建 token（包含 role）
    token = utils.create_access_token({"sub": user.id, "role": user.role.value})

    return utils.success(
        {
            "user_id": user.id,
            "role": user.role.value,
            "access_token": token,
        },
        "User registered and activated",
    )


# ============================
#   登录 Login
# ============================
@router.post("/login")
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):

    user = crud.authenticate(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail=utils.error("Invalid credentials", "UNAUTHORIZED"))

    token = utils.create_access_token({"sub": user.id, "role": user.role.value})

    return utils.success(
        {
            "access_token": token,
            "role": user.role.value,
        },
        "Login success"
    )


# ============================
#     从 Header 提取 token
# ============================
def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail=utils.error("Missing token", "UNAUTHORIZED"))

    token = authorization.split(" ")[1].strip()
    payload = utils.decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail=utils.error("Invalid or expired token", "UNAUTHORIZED"))

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail=utils.error("Invalid token payload", "UNAUTHORIZED"))

    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=utils.error("User not found", "NOT_FOUND"))

    return user


# ============================
#     /me 获取用户信息
# ============================
@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return utils.success(
        {
            "user_id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "role": current_user.role.value
        },
        "OK"
    )
