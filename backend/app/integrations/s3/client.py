from __future__ import annotations

import boto3
from botocore.client import Config

from app.core.config import get_settings


def get_s3_client():
    settings = get_settings()
    session = boto3.session.Session()

    client_kwargs: dict[str, object] = {
        "service_name": "s3",
        "region_name": settings.aws_region,
        "endpoint_url": settings.s3_endpoint_url,
        "config": Config(s3={"addressing_style": "path" if settings.s3_use_path_style else "auto"}),
    }

    if settings.aws_access_key_id and settings.aws_secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

    return session.client(**client_kwargs)
