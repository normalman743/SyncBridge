# message 模型
from sqlalchemy import Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("blocks.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    text_content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    block = relationship("Block", back_populates="messages")
    files = relationship("File", back_populates="message", cascade="all, delete-orphan")
