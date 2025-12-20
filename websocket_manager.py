"""Compatibility shim for the legacy websocket manager import path."""

from app.services.websocket_manager import ConnectionManager, manager

__all__ = ["ConnectionManager", "manager"]
