from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import Role, User
from app.schemas.menu import (
    MenuItemCosting,
    MenuItemCreate,
    MenuItemRead,
    MenuItemUpdate,
    RecipeLineInput,
)
from app.services import menu as service

router = APIRouter(prefix="/menu", tags=["menu"])
_writer = require_roles(Role.MANAGER, Role.CHEF)


@router.get("/items", response_model=list[MenuItemRead])
def list_items(
    available_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return service.list_menu_items(db, available_only)


@router.post("/items", response_model=MenuItemRead, status_code=201)
def create_item(data: MenuItemCreate, db: Session = Depends(get_db), _: User = Depends(_writer)):
    return service.create_menu_item(db, data)


@router.get("/items/{item_id}", response_model=MenuItemRead)
def get_item(item_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return service.get_menu_item(db, item_id)


@router.patch("/items/{item_id}", response_model=MenuItemRead)
def update_item(
    item_id: int,
    data: MenuItemUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_writer),
):
    return service.update_menu_item(db, item_id, data)


@router.put("/items/{item_id}/recipe", response_model=MenuItemRead)
def set_recipe(
    item_id: int,
    lines: list[RecipeLineInput],
    db: Session = Depends(get_db),
    _: User = Depends(_writer),
):
    return service.set_recipe(db, item_id, lines)


@router.get("/items/{item_id}/costing", response_model=MenuItemCosting)
def costing(item_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return service.costing(db, item_id)
