from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.models.enums import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _build_claims(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    role: str | None = None,
    jti: str | None = None,
) -> dict[str, str | int]:
    settings = get_settings()
    now = datetime.now(UTC)
    claims: dict[str, str | int] = {
        "sub": subject,
        "type": token_type,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": jti or str(uuid4()),
    }
    if role is not None:
        claims["role"] = role
    return claims


def create_access_token(*, user_id: UUID, role: UserRole) -> str:
    settings = get_settings()
    claims = _build_claims(
        subject=str(user_id),
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        role=role.value,
    )
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(*, user_id: UUID) -> tuple[str, str]:
    settings = get_settings()
    jti = str(uuid4())
    claims = _build_claims(
        subject=str(user_id),
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        jti=jti,
    )
    token = jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


def decode_token(token: str) -> dict[str, str | int]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    return payload


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
