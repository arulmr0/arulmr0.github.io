"""FastAPI application factory."""

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import DEV_SECRET_KEY, Settings, get_settings
from app.core.database import SessionLocal, engine, get_db
from app.core.exceptions import DomainError
from app.models import Base

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
log = logging.getLogger("hfs")


def harden_secret_key(settings: Settings) -> bool:
    """Replace the shipped development secret with a random one.

    Returns True when a key was generated. Sessions then do not survive a restart,
    which is the safe failure mode for a deployment that forgot to set HFS_SECRET_KEY.
    """
    if settings.secret_key != DEV_SECRET_KEY:
        return False
    settings.secret_key = secrets.token_urlsafe(48)
    log.warning("HFS_SECRET_KEY is not set; generated a random key for this process")
    return True


def bootstrap_admin(settings: Settings) -> bool:
    """Create the configured admin account when it does not exist yet.

    Returns True when an account was created. Never changes an existing account.
    """
    if not (settings.admin_email and settings.admin_password):
        return False
    from app.core.exceptions import ConflictError
    from app.models.user import Role
    from app.schemas.auth import UserCreate
    from app.services.auth import create_user

    with SessionLocal() as db:
        try:
            create_user(
                db,
                UserCreate(
                    email=settings.admin_email,
                    full_name="Administrator",
                    password=settings.admin_password,
                    role=Role.ADMIN,
                ),
            )
        except ConflictError:
            return False
    log.info("Created admin account %s from HFS_ADMIN_EMAIL", settings.admin_email)
    return True


def setup_required(db: Session) -> bool:
    """True when nobody can log in because the database has no user at all."""
    from sqlalchemy import select

    from app.models.user import User

    return db.scalar(select(User.id).limit(1)) is None


def seed_if_requested(settings: Settings) -> None:
    if not settings.seed_on_start:
        return
    from app.seed import seed  # local import keeps seeding out of the request path

    with SessionLocal() as db:
        seed(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Development convenience: create tables on start-up. Production deployments
    # should manage schema changes with migrations (see docs/02-architecture.md).
    settings = get_settings()
    harden_secret_key(settings)
    Base.metadata.create_all(bind=engine)
    seed_if_requested(settings)
    bootstrap_admin(settings)
    with SessionLocal() as db:
        empty = setup_required(db)
    if empty:
        log.warning(
            "The database has no users, so nobody can log in. Set HFS_ADMIN_EMAIL and "
            "HFS_ADMIN_PASSWORD (or HFS_SEED_ON_START=true for demo data) and restart."
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    if not logging.getLogger().handlers:  # uvicorn only configures its own loggers
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s: %(message)s")
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Procurement, inventory, menu, sales, HR, payroll and reporting "
        "for a hotel food-service operation.",
        lifespan=lifespan,
    )

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.get("/health", tags=["system"])
    def health(db: Session = Depends(get_db)) -> dict[str, str | bool]:
        return {
            "status": "ok",
            "currency": settings.currency,
            # True means no account exists yet; see HFS_ADMIN_EMAIL in the README.
            "setup_required": setup_required(db),
        }

    app.include_router(api_router)

    if WEB_DIR.exists():

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(WEB_DIR / "index.html")

        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    return app


app = create_app()
