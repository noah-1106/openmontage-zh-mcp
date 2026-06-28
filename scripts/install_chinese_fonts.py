#!/usr/bin/env python3
"""Pre-download Chinese font fallbacks for OpenMontage.

Run this after installing dependencies to ensure CJK text renders correctly
in Pillow-based graphics and previews, even when the host system has no
Chinese fonts installed.

  python3 scripts/install_chinese_fonts.py

The script downloads a Noto Sans SC fallback into ~/.openmontage/fonts/.
It is safe to re-run; already-cached files are skipped.
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from tools.graphics.fonts import ensure_noto_sans_sc
    except Exception as exc:  # pragma: no cover
        print(f"[ERROR] Could not import font helper: {exc}", file=sys.stderr)
        print("Make sure you have installed the project dependencies.", file=sys.stderr)
        return 1

    try:
        path = ensure_noto_sans_sc(timeout=120.0)
    except Exception as exc:
        print(f"[ERROR] Failed to download Chinese font fallback: {exc}", file=sys.stderr)
        print(
            "Chinese text in rendered images/videos may appear as tofu boxes (□□□).",
            file=sys.stderr,
        )
        print(
            "If the download keeps failing, you can also copy any Noto Sans CJK / "
            "Source Han Sans / PingFang / Microsoft YaHei font file to ~/.openmontage/fonts/.",
            file=sys.stderr,
        )
        return 1

    print(f"[OK] Chinese font fallback ready: {path}")
    print("[TIP] Re-run this script anytime you want to refresh the cache.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
