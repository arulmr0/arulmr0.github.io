"""ORM models. Importing this package registers every table on the shared metadata."""

from app.models.base import Base
from app.models.hr import Attendance, Employee, SalaryAdvance
from app.models.inventory import Ingredient, StockMovement
from app.models.menu import MenuItem, RecipeLine
from app.models.order import Order, OrderLine, Payment
from app.models.payroll import PayrollRun, Payslip
from app.models.procurement import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine
from app.models.supplier import Supplier
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Supplier",
    "Ingredient",
    "StockMovement",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "GoodsReceipt",
    "GoodsReceiptLine",
    "MenuItem",
    "RecipeLine",
    "Order",
    "OrderLine",
    "Payment",
    "Employee",
    "Attendance",
    "SalaryAdvance",
    "PayrollRun",
    "Payslip",
]
