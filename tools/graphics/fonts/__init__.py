"""Font helper for graphics tools.

Provides a downloadable Noto Sans SC fallback so CJK text renders correctly
even when the host system has no Chinese fonts installed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

FONT_CACHE_DIR = Path.home() / ".openmontage" / "fonts"
NOTO_SANS_SC_URL = "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansSC-Regular.otf"
NOTO_SANS_SC_FILENAME = "NotoSansSC-Regular.otf"


def _ensure_font_cache_dir() -> Path:
    FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return FONT_CACHE_DIR


def get_cached_font_path(filename: str) -> Path | None:
    path = FONT_CACHE_DIR / filename
    if path.exists():
        return path
    return None


def download_font(url: str, filename: str, timeout: float = 120.0) -> Path:
    """Download a font file to the OpenMontage font cache.

    Returns the path to the cached font. Raises on network or write errors.
    """
    import requests

    cache_dir = _ensure_font_cache_dir()
    target = cache_dir / filename

    if target.exists():
        return target

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    target.write_bytes(response.content)
    return target


def ensure_noto_sans_sc(timeout: float = 120.0) -> Path:
    """Ensure Noto Sans SC Regular is available locally, downloading if needed."""
    cached = get_cached_font_path(NOTO_SANS_SC_FILENAME)
    if cached:
        return cached
    return download_font(NOTO_SANS_SC_URL, NOTO_SANS_SC_FILENAME, timeout=timeout)


def get_cjk_font(size: int = 18) -> Any:
    """Return a Pillow ImageFont instance capable of rendering CJK text.

    Prefers system-installed fonts (PingFang, STHeiti, WenQuanYi, Noto CJK),
    then falls back to a downloadable Noto Sans SC font cached under
    ~/.openmontage/fonts.
    """
    from PIL import ImageFont

    system_candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJKsc-Regular.otf",
    ]

    for path in system_candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue

    try:
        cached = ensure_noto_sans_sc()
        return ImageFont.truetype(str(cached), size)
    except Exception:
        pass

    return ImageFont.load_default()


def get_font_pair(body_size: int = 18, title_size: int = 24) -> tuple[Any, Any]:
    """Return (body_font, title_font) for graphics rendering.

    Both fonts support CJK text. If the underlying font is a TrueType/OTF file,
    the title font is the same face at a larger size.
    """
    from PIL import ImageFont

    body_font = get_cjk_font(body_size)

    if title_size == body_size:
        return body_font, body_font

    # Try to reload the same source at title_size.
    title_font: Any | None = None
    try:
        source = getattr(body_font, "path", None)
        if source:
            title_font = ImageFont.truetype(source, title_size)
    except (IOError, OSError, AttributeError):
        pass

    if title_font is None:
        title_font = body_font

    return body_font, title_font
