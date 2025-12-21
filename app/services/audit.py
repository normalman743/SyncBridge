"""
Isolated audit logging service.
All writes are wrapped in try-except to ensure failures never interrupt main business logic.
"""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def log_audit(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    user_id: int | None = None,
    old_data: dict[str, Any] | None = None,
    new_data: dict[str, Any] | None = None,
) -> None:
    """
    Write an audit log entry. Failures are logged but do not raise exceptions.
    
    Args:
        db: Database session
        entity_type: One of: form, function, nonfunction, message, file
        entity_id: ID of the entity being audited
        action: One of: create, update, delete, status_change, merge_subform
        user_id: User performing the action (nullable for system actions)
        old_data: Previous state snapshot (JSON-serializable dict)
        new_data: New state snapshot (JSON-serializable dict)
    """
    try:
        audit = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            old_data=old_data,
            new_data=new_data,
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.error(f"Audit log write failed: {e}", exc_info=True)
        db.rollback()
