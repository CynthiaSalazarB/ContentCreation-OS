from __future__ import annotations

from core.paths import PERSONAL_BRAND_PATH


def load_personal_brand() -> str:
    if not PERSONAL_BRAND_PATH.exists():
        raise FileNotFoundError(f"Brand file not found: {PERSONAL_BRAND_PATH}")
    return PERSONAL_BRAND_PATH.read_text(encoding="utf-8")
