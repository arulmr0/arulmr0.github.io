from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MenuItem(TimestampMixin, Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="main", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    recipe: Mapped[list["RecipeLine"]] = relationship(
        back_populates="menu_item", cascade="all, delete-orphan"
    )


class RecipeLine(Base):
    """Bill of materials: how much of each ingredient one portion consumes."""

    __tablename__ = "recipe_lines"
    __table_args__ = (UniqueConstraint("menu_item_id", "ingredient_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id"), index=True, nullable=False
    )
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)

    menu_item: Mapped[MenuItem] = relationship(back_populates="recipe")
    ingredient = relationship("Ingredient")
