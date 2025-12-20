from sqlalchemy import String, Integer, DateTime, Enum, ForeignKey, Text, func, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Form(Base):
    __tablename__ = "forms"
    __table_args__ = (
        Index("ix_forms_user_id", "user_id"),
        Index("ix_forms_developer_id", "developer_id"),
        # 确保一个 subform 只能被一个 mainform 指向；MySQL 允许多个 NULL
        UniqueConstraint("subform_id", name="uq_forms_subform_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    type: Mapped[str] = mapped_column(
        Enum("mainform", "subform", name="form_type"),
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)             # client
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # 接单 developer
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)          # 创建人

    title: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    budget: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_time: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("preview", "available", "processing", "rewrite", "end", "error", name="form_status"),
        nullable=False,
        default="preview",
    )

    subform_id: Mapped[int | None] = mapped_column(ForeignKey("forms.id"), nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    client = relationship("User", foreign_keys=[user_id], back_populates="forms_as_client")
    developer = relationship("User", foreign_keys=[developer_id], back_populates="forms_as_developer")

    subform = relationship("Form", foreign_keys=[subform_id], uselist=False)

    functions = relationship("Function", back_populates="form", cascade="all, delete-orphan")
    nonfunctions = relationship("NonFunction", back_populates="form", cascade="all, delete-orphan")
    blocks = relationship("Block", back_populates="form", cascade="all, delete-orphan")