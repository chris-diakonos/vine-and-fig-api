"""
S3-compatible storage utilities for generated CLI artifacts.
"""
from pathlib import Path
from typing import Optional
from urllib.parse import quote
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class S3Storage:
    """Uploads generated artifacts to S3-compatible object storage."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
        prefix: Optional[str] = None,
    ):
        self.bucket_name = bucket_name or settings.s3_bucket_name
        self.endpoint_url = endpoint_url or settings.s3_endpoint_url or None
        self.access_key_id = access_key_id or settings.s3_access_key_id or None
        self.secret_access_key = secret_access_key or settings.s3_secret_access_key or None
        self.region_name = region_name or settings.s3_region_name
        self.prefix = prefix if prefix is not None else settings.s3_prefix

        if not self.bucket_name:
            raise ValueError("S3 bucket name is required. Set S3_BUCKET_NAME or pass --bucket.")

    def _client(self):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for S3 uploads. Install project requirements first.") from exc

        kwargs = {
            "service_name": "s3",
            "region_name": self.region_name,
        }
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        if self.access_key_id and self.secret_access_key:
            kwargs["aws_access_key_id"] = self.access_key_id
            kwargs["aws_secret_access_key"] = self.secret_access_key

        return boto3.client(**kwargs)

    def object_key(self, key: str) -> str:
        key = key.lstrip("/")
        prefix = (self.prefix or "").strip("/")
        return f"{prefix}/{key}" if prefix else key

    def upload_file(self, file_path: Path, key: str, content_type: Optional[str] = None) -> str:
        object_key = self.object_key(key)
        extra_args = {"ContentType": content_type} if content_type else None

        upload_kwargs = {
            "Filename": str(file_path),
            "Bucket": self.bucket_name,
            "Key": object_key,
        }
        if extra_args:
            upload_kwargs["ExtraArgs"] = extra_args

        self._client().upload_file(**upload_kwargs)
        logger.info("Uploaded %s to s3://%s/%s", file_path, self.bucket_name, object_key)
        return self.object_url(object_key)

    def object_url(self, object_key: str) -> str:
        if self.endpoint_url:
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{quote(object_key)}"
        return f"s3://{self.bucket_name}/{object_key}"
