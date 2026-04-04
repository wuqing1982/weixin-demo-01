import os


def _normalize_base_url(value: str | None) -> str:
    if not value:
        return ''
    return value.rstrip('/')


PUBLIC_BASE_URL = _normalize_base_url(os.getenv('PUBLIC_BASE_URL', 'https://e.cps.vin'))
