from __future__ import annotations

import shutil
import time
from pathlib import Path

from .base import ConnectionTestResult, FileInfo, StorageUsage

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
_AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".aac"}
_USAGE_CACHE_TTL = 300


class LocalStorage:
    def __init__(self, root_dir: str, repo_root: Path | None = None):
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[3]
        self.root = repo_root / root_dir
        self._usage_cache: StorageUsage | None = None
        self._usage_cache_time: float = 0

    def upload(self, path: str, content: bytes, content_type: str) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return f"/{target.relative_to(self.root.parent.parent)}"

    def download(self, path: str) -> bytes:
        target = self._resolve(path)
        return target.read_bytes()

    def delete(self, path: str) -> bool:
        target = self._resolve(path)
        if target.exists():
            target.unlink()
            return True
        return False

    def get_usage(self) -> StorageUsage:
        now = time.monotonic()
        if self._usage_cache and (now - self._usage_cache_time) < _USAGE_CACHE_TTL:
            return self._usage_cache

        total_bytes = 0
        file_count = 0
        by_type: dict[str, int] = {}
        deadline = time.monotonic() + 10

        if self.root.exists():
            for entry in self.root.rglob("*"):
                if time.monotonic() > deadline:
                    break
                if entry.is_file():
                    try:
                        size = entry.stat().st_size
                        total_bytes += size
                        file_count += 1
                        ext = entry.suffix.lower()
                        if ext in _IMAGE_EXTS:
                            by_type["图片"] = by_type.get("图片", 0) + size
                        elif ext in _AUDIO_EXTS:
                            by_type["音频"] = by_type.get("音频", 0) + size
                        else:
                            by_type["其他"] = by_type.get("其他", 0) + size
                    except OSError:
                        pass

        disk_usage = shutil.disk_usage(self.root) if self.root.exists() else shutil.disk_usage(".")
        usage = StorageUsage(
            total_bytes=disk_usage.total,
            used_bytes=total_bytes,
            file_count=file_count,
            by_type=by_type,
        )
        self._usage_cache = usage
        self._usage_cache_time = now
        return usage

    def test_connection(self) -> ConnectionTestResult:
        try:
            if not self.root.exists():
                self.root.mkdir(parents=True, exist_ok=True)
            test_file = self.root / ".storage_test"
            test_file.write_text("ok")
            content = test_file.read_text()
            test_file.unlink()
            if content == "ok":
                return ConnectionTestResult(ok=True, message="本地存储连接正常")
            return ConnectionTestResult(ok=False, message="读写验证失败")
        except Exception as exc:
            return ConnectionTestResult(ok=False, message=f"本地存储不可用: {exc}")

    def list_files(self, prefix: str, limit: int) -> list[FileInfo]:
        results: list[FileInfo] = []
        search_dir = self.root / prefix if prefix else self.root
        if not search_dir.exists():
            return results
        for entry in search_dir.rglob("*"):
            if len(results) >= limit:
                break
            if entry.is_file():
                try:
                    st = entry.stat()
                    results.append(FileInfo(
                        path=str(entry.relative_to(self.root)),
                        size_bytes=st.st_size,
                        last_modified=None,
                    ))
                except OSError:
                    pass
        return results

    def _resolve(self, path: str) -> Path:
        relative = path.lstrip("/")
        return self.root.parent.parent / relative
