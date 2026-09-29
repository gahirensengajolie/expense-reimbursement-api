from collections import defaultdict, deque
from time import monotonic
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserOut, LoginRequest, TokenPair, RefreshRequest
from fastapi.security import OAuth2PasswordRequestForm
from app.core.deps import get_current_user
from app.models.user import User


router = APIRouter(prefix="/auth", tags=["auth"])
_login_attempts: dict[str, deque[float]] = defaultdict(deque)
_LOGIN_WINDOW_SECONDS = 60.0
_LOGIN_MAX_ATTEMPTS = 5


def reset_login_limits() -> None:
    """Reset process-local limits on startup and in isolated test clients."""
    _login_attempts.clear()


@router.get("/me", response_model=UserOut)
def current_user(user: User = Depends(get_current_user)):
    """Return the authenticated profile for frontend session hydration."""
    return user

@router.post(
    "/token",
    response_model=TokenPair,
    include_in_schema=False,
)
def token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    _enforce_login_limit(request, form_data.username)

    service = AuthService(db)

    user = service.authenticate(
        email=form_data.username,
        password=form_data.password,
    )

    access_token, refresh_token = service.issue_tokens(user)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


def _enforce_login_limit(request: Request, email: str) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}:{email.lower()}"
    now = monotonic()
    attempts = _login_attempts[key]
    while attempts and now - attempts[0] >= _LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many login attempts")
    attempts.append(now)


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register(payload.email, payload.password, payload.full_name)


@router.post("/login", response_model=TokenPair)
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    _enforce_login_limit(request, str(payload.email))
    service = AuthService(db)
    user = service.authenticate(payload.email, payload.password)
    access_token, refresh_token = service.issue_tokens(user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    access_token, refresh_token = service.refresh_tokens(payload.refresh_token)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)
