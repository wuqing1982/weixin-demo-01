from __future__ import annotations

import time
from typing import Any

from .base import ConnectionTestResult, FileInfo, StorageUsage

_USAGE_CACHE_TTL = 300


class TencentCOSStorage:
    def __init__(self, config: dict[str, Any]):
        self.secret_id = config.get("secret_id", "")
        self.secret_key = config.get("secret_key", "")
        self.region = config.get("region", "")
        self.bucket = config.get("bucket", "")
        self.public_url = config.get("public_url", "").rstrip("/")
        self._client = None
        self._usage_cache: StorageUsage | None = None
        self._usage_cache_time: float = 0

    def _get_client(self):
        if self._client is None:
            from qcloud_cos import CosConfig, CosS3Client
            cos_config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key,
            )
            self._client = CosS3Client(cos_config)
        return self._client

    def upload(self, path: str, content: bytes, content_type: str) -> str:
        self._get_client().put_object(
            Bucket=self.bucket, Key=path, Body=content, ContentType=content_type
        )
        return f"{self.public_url}/{path}" if self.public_url else path

    def download(self, path: str) -> bytes:
        resp = self._get_client().get_object(Bucket=self.bucket, Key=path)
        return resp["Body"].get_stream().read()

    def delete(self, path: str) -> bool:
        self._get_client().delete_object(Bucket=self.bucket, Key=path)
        return True

    def get_usage(self) -> StorageUsage:
        now = time.monotonic()
        if self._usage_cache and (now - self._usage_cache_time) < _USAGE_CACHE_TTL:
            return self._usage_cache

        total_bytes = 0
        file_count = 0
        by_type: dict[str, int] = {}
        deadline = time.monotonic() + 10
        marker = ""

        try:
            while time.monotonic() < deadline:
                resp = self._get_client().list_objects(
                    Bucket=self.bucket, Prefix="", Marker=marker, MaxKeys=1000
                )
                for obj in resp.get("Contents", []):
                    size = int(obj.get("Size", 0))
                    total_bytes += size
                    file_count += 1
                    key = obj.get("Key", "")
                    ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
                    if ext in {"jpg", "jpeg", "png", "webp", "gif", "bmp"}:
                        by_type["图片"] = by_type.get("图片", 0) + size
                    elif ext in {"mp3", "wav", "ogg", "m4a"}:
                        by_type["音频"] = by_type.get("音频", 0) + size
                    else:
                        by_type["其他"] = by_type.get("其他", 0) + size
                if resp.get("IsTruncated") == "true":
                    marker = resp.get("NextMarker", "")
                else:
                    break
        except Exception:
            pass

        usage = StorageUsage(
            total_bytes=0, used_bytes=total_bytes, file_count=file_count, by_type=by_type
        )
        self._usage_cache = usage
        self._usage_cache_time = now
        return usage

    def test_connection(self) -> ConnectionTestResult:
        try:
            self._get_client().head_bucket(Bucket=self.bucket)
            return ConnectionTestResult(ok=True, message="腾讯云 COS 连接正常")
        except Exception as exc:
            self._client = None
            return ConnectionTestResult(ok=False, message=f"COS 连接失败: {exc}")

    def list_files(self, prefix: str, limit: int) -> list[FileInfo]:
        results: list[FileInfo] = []
        try:
            resp = self._get_client().list_objects(
                Bucket=self.bucket, Prefix=prefix, MaxKeys=limit
            )
            for obj in resp.get("Contents", []):
                results.append(FileInfo(
                    path=obj.get("Key", ""),
                    size_bytes=int(obj.get("Size", 0)),
                    last_modified=obj.get("LastModified", ""),
                ))
        except Exception:
            pass
        return results
