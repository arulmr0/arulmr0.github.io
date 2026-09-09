from datetime import date

from pydantic import BaseModel


class SalesSummary(BaseModel):
    date_from: date
    date_to: date
    orders_paid: int
    orders_cancelled: int
    gross_sales_minor: int
    tax_collected_minor: int
    net_sales_minor: int
    food_cost_minor: int
    gross_margin_minor: int
    gross_margin_percent: float
    average_ticket_minor: int


class TopItem(BaseModel):
    menu_item_id: int
    code: str
    name: str
    quantity_sold: int
    revenue_minor: int


class SupplierSpend(BaseModel):
    supplier_id: int
    supplier_name: str
    purchase_orders: int
    received_value_minor: int


class DashboardSummary(BaseModel):
    today_sales_minor: int
    today_orders: int
    open_orders: int
    low_stock_items: int
    open_purchase_orders: int
    active_employees: int
    inventory_value_minor: int
    reservations_today: int
