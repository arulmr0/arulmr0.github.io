"""FastAPI application factory."""

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import DEV_SECRET_KEY, Settings, get_settings
from app.core.database import SessionLocal, engine
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
    yield


def create_app() -> FastAPI:
    settings = get_settings()
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
    def health() -> dict[str, str]:
        return {"status": "ok", "currency": settings.currency}

    app.include_router(api_router)

    if WEB_DIR.exists():

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(WEB_DIR / "index.html")

        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    return app


app = create_app()
