from __future__ import annotations

from app.core.config import get_settings
from app.integrations.s3.client import get_s3_client


def generate_presigned_download(*, object_key: str, filename: str) -> str:
    settings = get_settings()
    s3 = get_s3_client()

    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": settings.s3_bucket_name,
            "Key": object_key,
            "ResponseContentDisposition": f'attachment; filename="{filename}"',
        },
        ExpiresIn=settings.s3_presigned_expire_seconds,
    )
