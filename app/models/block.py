from sqlalchemy import Integer, DateTime, Enum, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = (
        Index("ix_blocks_form_id", "form_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id"), nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("urgent", "normal", name="block_status"),
        nullable=False,
        default="normal",
    )
    type: Mapped[str] = mapped_column(
        Enum("general", "function", "nonfunction", name="block_type"),
        nullable=False,
        default="general",
    )
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())

    form = relationship("Form", back_populates="blocks")
    messages = relationship("Message", back_populates="block", cascade="all, delete-orphan")