from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import Role, User
from app.schemas.payroll import PayrollRunCreate, PayrollRunRead
from app.services import payroll as service

router = APIRouter(prefix="/payroll", tags=["payroll"])
_payroll = require_roles(Role.ACCOUNTANT, Role.HR, Role.MANAGER)


@router.get("/runs", response_model=list[PayrollRunRead])
def list_runs(db: Session = Depends(get_db), _: User = Depends(_payroll)):
    return service.list_runs(db)


@router.post("/runs", response_model=PayrollRunRead, status_code=201)
def create_run(
    data: PayrollRunCreate, db: Session = Depends(get_db), user: User = Depends(_payroll)
):
    return service.create_run(db, data, user.id)


@router.get("/runs/{run_id}", response_model=PayrollRunRead)
def get_run(run_id: int, db: Session = Depends(get_db), _: User = Depends(_payroll)):
    return service.get_run(db, run_id)


@router.post("/runs/{run_id}/recompute", response_model=PayrollRunRead)
def recompute(run_id: int, db: Session = Depends(get_db), _: User = Depends(_payroll)):
    return service.recompute_run(db, run_id)


@router.post("/runs/{run_id}/finalize", response_model=PayrollRunRead)
def finalize(run_id: int, db: Session = Depends(get_db), _: User = Depends(_payroll)):
    return service.finalize_run(db, run_id)


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: int, db: Session = Depends(get_db), _: User = Depends(_payroll)):
    service.delete_run(db, run_id)
    return Response(status_code=204)
