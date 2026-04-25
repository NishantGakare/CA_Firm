from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import UserRole
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def register_client(self, payload: RegisterRequest) -> User:
        existing = self.db.scalar(select(User).where(User.email == payload.email.lower()))
        if existing is not None:
            raise ValueError("Email already registered")

        user = User(
            full_name=payload.full_name.strip(),
            email=payload.email.lower(),
            phone=payload.phone,
            password_hash=hash_password(payload.password.get_secret_value()),
            role=UserRole.CLIENT,
            is_active=True,
            is_verified=False,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, payload: LoginRequest, *, ip: str | None, user_agent: str | None) -> tuple[User, TokenPair]:
        user = self.db.scalar(select(User).where(User.email == payload.email.lower()))
        if user is None or not verify_password(payload.password.get_secret_value(), user.password_hash):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("User is inactive")

        user.last_login_at = datetime.now(UTC)
        tokens = self._issue_token_pair(user, ip=ip, user_agent=user_agent)
        self.db.commit()
        return user, tokens

    def refresh(self, refresh_token: str, *, ip: str | None, user_agent: str | None) -> TokenPair:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        user_id = UUID(str(payload["sub"]))
        jti = str(payload.get("jti", ""))
        if not jti:
            raise ValueError("Invalid refresh token")

        session = self.db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
        if session is None:
            raise ValueError("Refresh token not found")
        if session.user_id != user_id:
            raise ValueError("Refresh token user mismatch")
        if session.revoked_at is not None:
            raise ValueError("Refresh token revoked")
        if session.expires_at <= datetime.now(UTC):
            raise ValueError("Refresh token expired")
        if session.token_hash != hash_token(refresh_token):
            raise ValueError("Refresh token hash mismatch")

        user = self.db.get(User, user_id)
        if user is None or not user.is_active:
            raise ValueError("User is unavailable")

        session.revoked_at = datetime.now(UTC)
        tokens = self._issue_token_pair(user, ip=ip, user_agent=user_agent)
        self.db.commit()
        return tokens

    def logout(self, refresh_token: str) -> None:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        jti = str(payload.get("jti", ""))
        if not jti:
            raise ValueError("Invalid refresh token")

        session = self.db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            self.db.commit()

    def _issue_token_pair(self, user: User, *, ip: str | None, user_agent: str | None) -> TokenPair:
        access_token = create_access_token(user_id=user.id, role=user.role)
        refresh_token, jti = create_refresh_token(user_id=user.id)

        token_session = RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days),
            issued_ip=ip,
            issued_user_agent=user_agent,
        )
        self.db.add(token_session)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
        )
