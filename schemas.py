"""Compatibility shim for legacy schema imports."""

from app.schemas import (
    AuthMeOut,
    FileOut,
    FormCreate,
    FormOut,
    FunctionIn,
    FunctionOut,
    LoginIn,
    MessageIn,
    MessageOut,
    RegisterIn,
    Resp,
)

__all__ = [
    "Resp",
    "RegisterIn",
    "LoginIn",
    "AuthMeOut",
    "FormCreate",
    "FormOut",
    "FunctionIn",
    "FunctionOut",
    "MessageIn",
    "MessageOut",
    "FileOut",
]
