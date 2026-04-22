from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class StorageUsage:
    total_bytes: int
    used_bytes: int
    file_count: int
    by_type: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ConnectionTestResult:
    ok: bool
    message: str


@dataclass(frozen=True)
class FileInfo:
    path: str
    size_bytes: int
    last_modified: str | None = None


class StorageBackend(Protocol):
    def upload(self, path: str, content: bytes, content_type: str) -> str: ...
    def download(self, path: str) -> bytes: ...
    def delete(self, path: str) -> bool: ...
    def get_usage(self) -> StorageUsage: ...
    def test_connection(self) -> ConnectionTestResult: ...
    def list_files(self, prefix: str, limit: int) -> list[FileInfo]: ...
