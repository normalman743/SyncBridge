import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY.strip().lower() == "secret":
    raise RuntimeError("SECRET_KEY must be set to a non-default value for token signing.")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return _pwd_ctx.hash(password)


def verify_password(plain_password: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain_password, hashed)


def create_access_token(data: dict, expires_delta: int | None = None) -> str:
    to_encode = data.copy()
    if to_encode.get("sub") is None:
        raise ValueError("Token payload must include 'sub'")
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=(expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        return None
    except JWTError:
        return None


# Backward-compatible alias

def decode_token(token: str) -> dict | None:
    return decode_access_token(token)
