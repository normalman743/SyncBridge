from sqlalchemy import String, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class License(Base):
    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    license_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    role: Mapped[str] = mapped_column(
        Enum("client", "developer", name="license_role"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum("unused", "active", "expired", "revoked", name="license_status"),
        nullable=False,
        default="unused",
    )

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    activated_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="licenses")
