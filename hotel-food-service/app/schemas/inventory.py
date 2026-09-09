from datetime import datetime

from pydantic import BaseModel, Field

from app.models.inventory import MovementType, Unit
from app.schemas.common import ORMModel


class IngredientCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=150)
    category: str = "general"
    unit: Unit
    reorder_level: float = Field(default=0, ge=0)
    avg_cost_minor: int = Field(default=0, ge=0)


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    category: str | None = None
    reorder_level: float | None = Field(default=None, ge=0)
    is_active: bool | None = None


class IngredientRead(ORMModel):
    id: int
    sku: str
    name: str
    category: str
    unit: Unit
    reorder_level: float
    avg_cost_minor: int
    quantity_on_hand: float
    is_active: bool

    @property
    def below_reorder_level(self) -> bool:
        return self.quantity_on_hand <= self.reorder_level


class StockAdjustment(BaseModel):
    """Manual stock correction or wastage entry."""

    movement_type: MovementType = MovementType.ADJUSTMENT
    quantity: float = Field(description="Signed quantity. Negative removes stock.")
    note: str | None = Field(default=None, max_length=255)


class StockMovementRead(ORMModel):
    id: int
    ingredient_id: int
    movement_type: MovementType
    quantity: float
    unit_cost_minor: int
    reference_type: str | None
    reference_id: int | None
    note: str | None
    created_at: datetime


class LowStockItem(BaseModel):
    ingredient_id: int
    sku: str
    name: str
    unit: Unit
    quantity_on_hand: float
    reorder_level: float
    shortfall: float


class InventoryValuation(BaseModel):
    total_value_minor: int
    items: int
