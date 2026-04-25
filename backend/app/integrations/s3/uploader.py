from __future__ import annotations

from app.core.config import get_settings
from app.integrations.s3.client import get_s3_client


def generate_presigned_upload(*, object_key: str, content_type: str) -> dict[str, object]:
    settings = get_settings()
    s3 = get_s3_client()

    return s3.generate_presigned_post(
        Bucket=settings.s3_bucket_name,
        Key=object_key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, 25 * 1024 * 1024],
        ],
        ExpiresIn=settings.s3_presigned_expire_seconds,
    )
