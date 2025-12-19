from sqlalchemy import String, Integer, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(32), nullable=False)

    # 注意：这里按 pasted.txt，包含 admin。若你们最终不要 admin，把 'admin' 删掉即可。
    role: Mapped[str | None] = mapped_column(
        Enum("client", "developer", "admin", name="user_role"),
        nullable=True,
    )
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    licenses = relationship("License", back_populates="user", uselist=False)
    forms_as_client = relationship("Form", foreign_keys="Form.user_id", back_populates="client")
    forms_as_developer = relationship("Form", foreign_keys="Form.developer_id", back_populates="developer")
