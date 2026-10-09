import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings, validate_production_settings
from app.core.database import Base, SessionLocal, engine
from app.exceptions import (
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.routers import admin, auth, expenses
from app.services.admin_service import AdminService

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("passbook")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Expense & Reimbursement API",
    description="A secure API for employee expense approval and reimbursement workflows.",
    version="1.1.0",
)


@app.on_event("startup")
def reset_runtime_limits():
    validate_production_settings(settings)
    logger.info("Starting in %s mode (database: %s)", settings.environment,
                settings.database_url.split(":", 1)[0])
    if settings.first_admin_email and settings.first_admin_password:
        with SessionLocal() as db:
            AdminService(db).ensure_first_admin(
                settings.first_admin_email, settings.first_admin_password
            )
    auth.reset_login_limits()


def _error_handler(status_code: int):
    async def handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status_code,
            content={"detail": exc.message},
        )

    return handler


app.add_exception_handler(NotFoundError, _error_handler(404))
app.add_exception_handler(ForbiddenError, _error_handler(403))
app.add_exception_handler(ConflictError, _error_handler(409))
app.add_exception_handler(BadRequestError, _error_handler(400))
app.add_exception_handler(AuthenticationError, _error_handler(401))


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        raise
    # Method, path, status and timing only: never bodies, tokens or query strings.
    logger.info("%s %s -> %s (%.0f ms)", request.method, request.url.path,
                response.status_code, (time.perf_counter() - started) * 1000)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    return response


app.include_router(auth.router)
app.include_router(expenses.router)
app.include_router(admin.router)


@app.get(
    "/health",
    tags=["system"],
    summary="Health check",
)
def health_check():
    return {
        "status": "ok",
        "service": "expense-reimbursement-api",
        "version": "1.1.0",
    }


# Serve the React production build from the same FastAPI origin.
# Vite writes to frontend/dist; the source directory remains available for npm run dev.
# This catch-all is intentionally last so API and health routes always win.
frontend_root = Path(__file__).resolve().parent.parent / "frontend"
frontend_dir = frontend_root / "dist" if (frontend_root / "dist").exists() else frontend_root
if (frontend_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    # No frontend build present (API-only deployment): give "/" a useful answer.
    @app.get("/", include_in_schema=False)
    def root():
        return {"service": "expense-reimbursement-api", "docs": "/docs", "health": "/health"}
