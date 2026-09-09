from sqlalchemy import func, select

from app.models import Employee, Ingredient, MenuItem, Order, PurchaseOrder, User
from app.seed import seed


def test_seed_is_idempotent_and_consistent(db, capsys):
    seed(db)
    seed(db)  # second call must be a no-op
    assert "already seeded" in capsys.readouterr().out
    assert db.scalar(select(func.count(User.id))) == 7
    assert db.scalar(select(func.count(Ingredient.id))) == 10
    assert db.scalar(select(func.count(MenuItem.id))) == 4
    assert db.scalar(select(func.count(PurchaseOrder.id))) == 3
    assert db.scalar(select(func.count(Order.id))) == 4
    assert db.scalar(select(func.count(Employee.id))) == 5
    # every ingredient received stock and no balance went negative
    for ingredient in db.scalars(select(Ingredient)):
        assert ingredient.quantity_on_hand > 0
        assert ingredient.avg_cost_minor > 0
