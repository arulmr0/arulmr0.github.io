import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Role(enum.StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    CHEF = "chef"
    CASHIER = "cashier"
    STOREKEEPER = "storekeeper"
    HR = "hr"
    ACCOUNTANT = "accountant"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False, default=Role.CASHIER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
