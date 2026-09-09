from fastapi import APIRouter

from app.api.v1 import (
    auth,
    hr,
    inventory,
    menu,
    orders,
    payroll,
    procurement,
    reports,
    reservations,
    suppliers,
)

api_router = APIRouter(prefix="/api/v1")
for module in (
    auth,
    suppliers,
    inventory,
    procurement,
    menu,
    orders,
    reservations,
    hr,
    payroll,
    reports,
):
    api_router.include_router(module.router)
