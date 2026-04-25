from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_ca_admin, require_ca_or_staff, require_client, require_staff
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenPair,
    UserPublic,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_client(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResponse:
    service = AuthService(db)
    try:
        user = service.register_client(payload)
        _, tokens = service.login(
            LoginRequest(email=payload.email, password=payload.password),
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AuthResponse(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResponse:
    service = AuthService(db)
    try:
        user, tokens = service.login(
            payload,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return AuthResponse(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
def refresh_tokens(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenPair:
    service = AuthService(db)
    try:
        return service.refresh(
            payload.refresh_token,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    db: Session = Depends(get_db),
) -> None:
    service = AuthService(db)
    try:
        service.logout(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.get("/rbac/client", response_model=UserPublic)
def client_only(current_user: User = Depends(require_client)) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.get("/rbac/staff", response_model=UserPublic)
def staff_only(current_user: User = Depends(require_staff)) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.get("/rbac/ca", response_model=UserPublic)
def ca_only(current_user: User = Depends(require_ca_admin)) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.get("/rbac/ops", response_model=UserPublic)
def ca_or_staff_only(current_user: User = Depends(require_ca_or_staff)) -> UserPublic:
    return UserPublic.model_validate(current_user)
