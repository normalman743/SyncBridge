# block 模型
from sqlalchemy import Integer, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Block(Base):
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id"), nullable=False)

    # 注意：按 pasted.txt，这里只有 urgent/normal
    status: Mapped[str] = mapped_column(Enum("urgent", "normal", name="block_status"), nullable=False)

    type: Mapped[str] = mapped_column(
        Enum("general", "function", "nonfunction", name="block_type"),
        nullable=False,
    )
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())

    form = relationship("Form", back_populates="blocks")
    messages = relationship("Message", back_populates="block", cascade="all, delete-orphan")
