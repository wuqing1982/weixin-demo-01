import copy
import mimetypes
from pathlib import Path
from threading import Lock
from typing import Any

from .store_utils import build_object_id, ensure_json_file, read_json_file, utcnow_iso, write_json_file


class UploadStore:
    def __init__(self, data_file: Path, uploads_root: Path):
        self.data_file = data_file
        self.uploads_root = uploads_root
        self.lock = Lock()
        ensure_json_file(self.data_file, {'uploads': []})
        self.uploads_root.mkdir(parents=True, exist_ok=True)

    def create_upload(
        self,
        *,
        owner_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> dict[str, Any]:
        upload_id = build_object_id('upload')
        suffix = self._resolve_suffix(filename, content_type)
        upload_dir = self.uploads_root / upload_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f'source{suffix}'
        file_path.write_bytes(content)

        width, height = self._read_image_size(file_path)
        created_at = utcnow_iso()
        record = {
            'uploadId': upload_id,
            'ownerId': owner_id,
            'originalFilename': filename or f'source{suffix}',
            'contentType': content_type or mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream',
            'filePath': self._to_asset_path(file_path),
            'sizeBytes': len(content),
            'width': width,
            'height': height,
            'createdAt': created_at,
            'updatedAt': created_at,
        }

        with self.lock:
            payload = read_json_file(self.data_file)
            payload.setdefault('uploads', []).append(record)
            write_json_file(self.data_file, payload)

        return copy.deepcopy(record)

    def get_upload(self, upload_id: str) -> dict[str, Any] | None:
        with self.lock:
            uploads = read_json_file(self.data_file).get('uploads', [])

        for upload in uploads:
            if upload.get('uploadId') == upload_id:
                return copy.deepcopy(upload)
        return None

    def resolve_disk_path(self, file_path: str) -> Path:
        relative = file_path.lstrip('/')
        repo_root = self.data_file.resolve().parents[2]
        return repo_root / relative

    def _to_asset_path(self, file_path: Path) -> str:
        repo_root = self.data_file.resolve().parents[2]
        return f"/{file_path.resolve().relative_to(repo_root).as_posix()}"

    def _resolve_suffix(self, filename: str, content_type: str) -> str:
        suffix = Path(filename or '').suffix.lower()
        if suffix in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
            return '.jpg' if suffix == '.jpeg' else suffix

        mapping = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/webp': '.webp',
            'image/gif': '.gif',
        }
        return mapping.get(content_type or '', '.bin')

    def _read_image_size(self, file_path: Path) -> tuple[int | None, int | None]:
        try:
            from PIL import Image  # type: ignore
        except Exception:
            return None, None

        try:
            with Image.open(file_path) as image:
                width, height = image.size
                return int(width), int(height)
        except Exception:
            return None, None
