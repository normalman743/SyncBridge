"""Compatibility shim for legacy models import path."""

from app.models import *  # noqa: F401,F403

__all__ = [
    "User",
    "License",
    "Form",
    "Function",
    "NonFunction",
    "Block",
    "Message",
    "File",
]
