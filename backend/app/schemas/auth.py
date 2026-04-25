from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.models.enums import UserRole


def _normalize_auth_email(value: str) -> str:
    email = value.strip().lower()
    if email.count("@") != 1:
        raise ValueError("Email must contain a single @ character")

    local_part, domain_part = email.split("@", maxsplit=1)
    if not local_part:
        raise ValueError("Email local part cannot be empty")
    if not domain_part:
        raise ValueError("Email domain cannot be empty")
    if domain_part.startswith(".") or domain_part.endswith(".") or ".." in domain_part:
        raise ValueError("Email domain is invalid")
    if "." not in domain_part:
        raise ValueError("Email domain must contain a dot")

    return email


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    phone: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email_value(cls, value: str) -> str:
        return _normalize_auth_email(value)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: SecretStr

    @field_validator("email")
    @classmethod
    def validate_email_value(cls, value: str) -> str:
        return _normalize_auth_email(value)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    user: UserPublic
    tokens: TokenPair


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32)
