"""Menu engineering: items, recipes (bill of materials) and food-cost analysis."""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.menu import MenuItem, RecipeLine
from app.schemas.menu import MenuItemCosting, MenuItemCreate, MenuItemUpdate, RecipeLineInput
from app.services import inventory as inventory_service


def list_menu_items(db: Session, available_only: bool = False) -> list[MenuItem]:
    stmt = (
        select(MenuItem)
        .options(selectinload(MenuItem.recipe))
        .order_by(MenuItem.category, MenuItem.name)
    )
    if available_only:
        stmt = stmt.where(MenuItem.is_available.is_(True))
    return list(db.scalars(stmt))


def get_menu_item(db: Session, item_id: int) -> MenuItem:
    item = db.get(MenuItem, item_id, options=[selectinload(MenuItem.recipe)])
    if item is None:
        raise NotFoundError(f"Menu item {item_id} not found")
    return item


def create_menu_item(db: Session, data: MenuItemCreate) -> MenuItem:
    if db.scalar(select(MenuItem).where(MenuItem.code == data.code)):
        raise ConflictError(f"Menu item with code '{data.code}' already exists")
    item = MenuItem(**data.model_dump(exclude={"recipe"}))
    _apply_recipe(db, item, data.recipe)
    db.add(item)
    db.commit()
    return item


def update_menu_item(db: Session, item_id: int, data: MenuItemUpdate) -> MenuItem:
    item = get_menu_item(db, item_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    return item


def set_recipe(db: Session, item_id: int, lines: list[RecipeLineInput]) -> MenuItem:
    item = get_menu_item(db, item_id)
    _apply_recipe(db, item, lines)
    db.commit()
    return item


def _apply_recipe(db: Session, item: MenuItem, lines: list[RecipeLineInput]) -> None:
    seen: set[int] = set()
    item.recipe.clear()
    for line in lines:
        if line.ingredient_id in seen:
            raise ValidationError(f"Ingredient {line.ingredient_id} listed twice in recipe")
        seen.add(line.ingredient_id)
        inventory_service.get_ingredient(db, line.ingredient_id)
        item.recipe.append(RecipeLine(ingredient_id=line.ingredient_id, quantity=line.quantity))


def food_cost_minor(item: MenuItem) -> int:
    """Cost of one portion at current weighted-average ingredient costs."""
    total = Decimal(0)
    for line in item.recipe:
        total += Decimal(str(line.quantity)) * line.ingredient.avg_cost_minor
    return int(total.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def portions_available(item: MenuItem) -> float | None:
    if not item.recipe:
        return None
    return min(
        (line.ingredient.quantity_on_hand / line.quantity) for line in item.recipe if line.quantity
    )


def costing(db: Session, item_id: int) -> MenuItemCosting:
    item = get_menu_item(db, item_id)
    cost = food_cost_minor(item)
    return MenuItemCosting(
        menu_item_id=item.id,
        price_minor=item.price_minor,
        food_cost_minor=cost,
        gross_margin_minor=item.price_minor - cost,
        food_cost_percent=round(cost / item.price_minor * 100, 2) if item.price_minor else 0.0,
        portions_available=portions_available(item),
    )
