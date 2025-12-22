from sqlalchemy import String, Integer, DateTime, Enum, ForeignKey, Text, func, SmallInteger, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class NonFunction(Base):
    __tablename__ = "nonfunctions"
    __table_args__ = (
        Index("ix_nonfunctions_form_id", "form_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    level: Mapped[str] = mapped_column(Enum("lightweight", "commercial", "enterprise", name="nfr_level"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("preview", "available", "processing", "rewrite", "end", "error", name="item_status"),
        nullable=False,
        default="preview",
    )
    is_changed: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    form = relationship("Form", back_populates="nonfunctions")