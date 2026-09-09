import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow


class Unit(enum.StrEnum):
    KG = "kg"
    G = "g"
    L = "l"
    ML = "ml"
    PCS = "pcs"


class Ingredient(TimestampMixin, Base):
    """Item master for everything the kitchen buys and consumes."""

    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="general", nullable=False)
    unit: Mapped[Unit] = mapped_column(Enum(Unit), nullable=False)
    reorder_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Weighted-average cost per unit, maintained on each goods receipt.
    avg_cost_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Denormalised running balance; the ledger (StockMovement) is the source of truth.
    quantity_on_hand: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    movements: Mapped[list["StockMovement"]] = relationship(back_populates="ingredient")


class MovementType(enum.StrEnum):
    RECEIPT = "receipt"  # goods received from supplier (+)
    CONSUMPTION = "consumption"  # consumed by a paid order (-)
    WASTAGE = "wastage"  # spoilage/breakage (-)
    ADJUSTMENT = "adjustment"  # stock count correction (+/-)


class StockMovement(Base):
    """Append-only inventory ledger. Positive quantity = stock in, negative = stock out."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id"), index=True, nullable=False
    )
    movement_type: Mapped[MovementType] = mapped_column(Enum(MovementType), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(40))
    reference_id: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    ingredient: Mapped[Ingredient] = relationship(back_populates="movements")
