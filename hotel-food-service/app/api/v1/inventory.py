from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import Role, User
from app.schemas.inventory import (
    IngredientCreate,
    IngredientRead,
    IngredientUpdate,
    InventoryValuation,
    LowStockItem,
    StockAdjustment,
    StockMovementRead,
)
from app.services import inventory as service

router = APIRouter(prefix="/inventory", tags=["inventory"])
_writer = require_roles(Role.MANAGER, Role.STOREKEEPER, Role.CHEF)


@router.get("/ingredients", response_model=list[IngredientRead])
def list_ingredients(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return service.list_ingredients(db, include_inactive)


@router.post("/ingredients", response_model=IngredientRead, status_code=201)
def create_ingredient(
    data: IngredientCreate, db: Session = Depends(get_db), _: User = Depends(_writer)
):
    return service.create_ingredient(db, data)


@router.get("/ingredients/{ingredient_id}", response_model=IngredientRead)
def get_ingredient(
    ingredient_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    return service.get_ingredient(db, ingredient_id)


@router.patch("/ingredients/{ingredient_id}", response_model=IngredientRead)
def update_ingredient(
    ingredient_id: int,
    data: IngredientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_writer),
):
    return service.update_ingredient(db, ingredient_id, data)


@router.post(
    "/ingredients/{ingredient_id}/adjust", response_model=StockMovementRead, status_code=201
)
def adjust_stock(
    ingredient_id: int,
    data: StockAdjustment,
    db: Session = Depends(get_db),
    user: User = Depends(_writer),
):
    return service.adjust_stock(db, ingredient_id, data, user.id)


@router.get("/movements", response_model=list[StockMovementRead])
def list_movements(
    ingredient_id: int | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return service.list_movements(db, ingredient_id, limit)


@router.get("/low-stock", response_model=list[LowStockItem])
def low_stock(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return service.low_stock(db)


@router.get("/valuation", response_model=InventoryValuation)
def valuation(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return service.valuation(db)
