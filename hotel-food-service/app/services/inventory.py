"""Inventory: item master, append-only stock ledger, weighted-average costing."""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.inventory import Ingredient, MovementType, StockMovement
from app.schemas.inventory import (
    IngredientCreate,
    IngredientUpdate,
    InventoryValuation,
    LowStockItem,
    StockAdjustment,
)

EPSILON = 1e-9


def list_ingredients(db: Session, include_inactive: bool = False) -> list[Ingredient]:
    stmt = select(Ingredient).order_by(Ingredient.name)
    if not include_inactive:
        stmt = stmt.where(Ingredient.is_active.is_(True))
    return list(db.scalars(stmt))


def get_ingredient(db: Session, ingredient_id: int) -> Ingredient:
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise NotFoundError(f"Ingredient {ingredient_id} not found")
    return ingredient


def create_ingredient(db: Session, data: IngredientCreate) -> Ingredient:
    if db.scalar(select(Ingredient).where(Ingredient.sku == data.sku)):
        raise ConflictError(f"Ingredient with SKU '{data.sku}' already exists")
    ingredient = Ingredient(**data.model_dump())
    db.add(ingredient)
    db.commit()
    return ingredient


def update_ingredient(db: Session, ingredient_id: int, data: IngredientUpdate) -> Ingredient:
    ingredient = get_ingredient(db, ingredient_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ingredient, field, value)
    db.commit()
    return ingredient


def record_movement(
    db: Session,
    ingredient: Ingredient,
    movement_type: MovementType,
    quantity: float,
    *,
    unit_cost_minor: int | None = None,
    reference_type: str | None = None,
    reference_id: int | None = None,
    note: str | None = None,
    user_id: int | None = None,
    allow_negative: bool = False,
) -> StockMovement:
    """Append a ledger entry and update the ingredient's balance and average cost.

    The caller owns the transaction: this function flushes but does not commit,
    so multi-line operations (a goods receipt, an order payment) stay atomic.
    """
    if abs(quantity) < EPSILON:
        raise ValidationError("Movement quantity must be non-zero")
    if movement_type == MovementType.RECEIPT and quantity <= 0:
        raise ValidationError("Receipts must add stock")
    if movement_type in (MovementType.CONSUMPTION, MovementType.WASTAGE) and quantity >= 0:
        raise ValidationError(f"{movement_type.value} must remove stock")

    new_balance = ingredient.quantity_on_hand + quantity
    if new_balance < -EPSILON and not allow_negative:
        raise ConflictError(
            f"Insufficient stock for {ingredient.name}: have {ingredient.quantity_on_hand:g} "
            f"{ingredient.unit.value}, need {abs(quantity):g}"
        )

    if movement_type == MovementType.RECEIPT:
        if unit_cost_minor is None:
            raise ValidationError("Receipts require a unit cost")
        ingredient.avg_cost_minor = _weighted_average(
            ingredient.quantity_on_hand, ingredient.avg_cost_minor, quantity, unit_cost_minor
        )
    else:
        unit_cost_minor = ingredient.avg_cost_minor if unit_cost_minor is None else unit_cost_minor

    ingredient.quantity_on_hand = 0.0 if abs(new_balance) < EPSILON else new_balance
    movement = StockMovement(
        ingredient_id=ingredient.id,
        movement_type=movement_type,
        quantity=quantity,
        unit_cost_minor=unit_cost_minor,
        reference_type=reference_type,
        reference_id=reference_id,
        note=note,
        created_by=user_id,
    )
    db.add(movement)
    db.flush()
    return movement


def _weighted_average(on_hand: float, avg_cost: int, added_qty: float, added_cost: int) -> int:
    existing = max(on_hand, 0.0)
    total_qty = existing + added_qty
    if total_qty <= EPSILON:
        return added_cost
    value = Decimal(existing) * avg_cost + Decimal(added_qty) * added_cost
    return int((value / Decimal(total_qty)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def adjust_stock(
    db: Session, ingredient_id: int, data: StockAdjustment, user_id: int | None
) -> StockMovement:
    if data.movement_type not in (MovementType.ADJUSTMENT, MovementType.WASTAGE):
        raise ValidationError("Only adjustment or wastage movements can be recorded manually")
    ingredient = get_ingredient(db, ingredient_id)
    movement = record_movement(
        db,
        ingredient,
        data.movement_type,
        data.quantity,
        note=data.note,
        reference_type="manual",
        user_id=user_id,
    )
    db.commit()
    return movement


def list_movements(db: Session, ingredient_id: int | None = None, limit: int = 200):
    stmt = select(StockMovement).order_by(StockMovement.id.desc()).limit(limit)
    if ingredient_id is not None:
        stmt = stmt.where(StockMovement.ingredient_id == ingredient_id)
    return list(db.scalars(stmt))


def low_stock(db: Session) -> list[LowStockItem]:
    stmt = (
        select(Ingredient)
        .where(Ingredient.is_active.is_(True))
        .where(Ingredient.quantity_on_hand <= Ingredient.reorder_level)
        .order_by(Ingredient.name)
    )
    return [
        LowStockItem(
            ingredient_id=i.id,
            sku=i.sku,
            name=i.name,
            unit=i.unit,
            quantity_on_hand=i.quantity_on_hand,
            reorder_level=i.reorder_level,
            shortfall=max(i.reorder_level - i.quantity_on_hand, 0.0),
        )
        for i in db.scalars(stmt)
    ]


def valuation(db: Session) -> InventoryValuation:
    total = 0
    count = 0
    for ingredient in db.scalars(select(Ingredient).where(Ingredient.is_active.is_(True))):
        if ingredient.quantity_on_hand > 0:
            total += int(
                (Decimal(ingredient.quantity_on_hand) * ingredient.avg_cost_minor).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
            count += 1
    return InventoryValuation(total_value_minor=total, items=count)
