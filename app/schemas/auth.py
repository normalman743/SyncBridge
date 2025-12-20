from typing import Optional
from pydantic import BaseModel, EmailStr


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str]
    license_key: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AuthMeOut(BaseModel):
    user_id: int
    email: EmailStr
    display_name: Optional[str]
    role: Optional[str]
