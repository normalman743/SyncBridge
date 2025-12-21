from sqlalchemy import String, Integer, DateTime, Enum, JSON, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_user_id", "user_id"),
    )

    # Use Integer for SQLite autoincrement compatibility
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(
        Enum("form", "function", "nonfunction", "message", "file", name="audit_entity_type"),
        nullable=False,
    )
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(
        Enum("create", "update", "delete", "status_change", "merge_subform", name="audit_action"),
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
