from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CA Firm Management API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(..., alias="DATABASE_URL")

    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "ca-firm-api"
    jwt_audience: str = "ca-firm-users"

    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 15

    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "ap-south-1"
    s3_bucket_name: str = Field(..., alias="S3_BUCKET_NAME")
    s3_endpoint_url: str | None = None
    s3_use_path_style: bool = False
    s3_presigned_expire_seconds: int = 900
    storage_mode: str = "s3"
    app_base_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
