from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserOut, LoginRequest, TokenPair, RefreshRequest

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register(payload.email, payload.password, payload.full_name)


@router.post("/login", response_model=TokenPair)
@limiter.limit("5/minute")  # brute-force mitigation
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.authenticate(payload.email, payload.password)
    access_token, refresh_token = service.issue_tokens(user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    access_token, refresh_token = service.refresh_tokens(payload.refresh_token)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)
