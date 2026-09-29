from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.database import Base, engine
from app.exceptions import (
    NotFoundError,
    ForbiddenError,
    ConflictError,
    BadRequestError,
    AuthenticationError,
)
from app.routers import auth, expenses, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Expense & Reimbursement API",
    description="A secure API for employee expense approval and reimbursement workflows.",
    version="1.1.0",
)


@app.on_event("startup")
def reset_runtime_limits():
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


@app.middleware("http" )
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

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
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
