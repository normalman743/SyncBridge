from sqlalchemy import String, Integer, DateTime, Enum, SmallInteger, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # email 已有 UNIQUE 约束，这里索引可选；如需查询优化可保留
        Index("ix_users_email", "email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(32), nullable=False)

    role: Mapped[str | None] = mapped_column(
        Enum("client", "developer", "admin", name="user_role"),
        nullable=True,
    )
    # 默认未激活，更贴合“注册→激活”的流程
    is_active: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    licenses = relationship("License", back_populates="user", uselist=False)
    forms_as_client = relationship("Form", foreign_keys="Form.user_id", back_populates="client")
    forms_as_developer = relationship("Form", foreign_keys="Form.developer_id", back_populates="developer")