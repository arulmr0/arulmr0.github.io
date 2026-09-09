from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class RecipeLineInput(BaseModel):
    ingredient_id: int
    quantity: float = Field(gt=0)


class MenuItemCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=150)
    category: str = "main"
    description: str | None = None
    price_minor: int = Field(ge=0)
    recipe: list[RecipeLineInput] = Field(default_factory=list)


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    category: str | None = None
    description: str | None = None
    price_minor: int | None = Field(default=None, ge=0)
    is_available: bool | None = None


class RecipeLineRead(ORMModel):
    id: int
    ingredient_id: int
    quantity: float


class MenuItemRead(ORMModel):
    id: int
    code: str
    name: str
    category: str
    description: str | None
    price_minor: int
    is_available: bool
    recipe: list[RecipeLineRead]


class MenuItemCosting(BaseModel):
    menu_item_id: int
    price_minor: int
    food_cost_minor: int
    gross_margin_minor: int
    food_cost_percent: float
    portions_available: float | None = Field(
        description="How many portions current stock supports; null when no recipe."
    )
