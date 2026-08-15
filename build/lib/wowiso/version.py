# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Version accessor. §3.9.
The version is **not set here** — it is derived by ``scripts/update-version.sh``
(the canonical stamper from the Admin-Manual) into ``version.txt`` /
``version.json``. This module only *reads* it, so the codebase can never drift
from the stamped value. Scheme: ``MAJOR.MINOR.BUILD`` (BUILD = epoch-min %
100000); ``versionCode = MAJOR*100000 + MINOR``.
"""
from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VERSION_FILE = _REPO_ROOT / "version.txt"
_VERSION_JSON = _REPO_ROOT / "version.json"
_FALLBACK = "0.0.00000"


def current(path: Path | None = None) -> str:
    """The stamped display version, e.g. ``'1.1.74918'``. Reads ``version.txt``."""
    p = path or _VERSION_FILE
    try:
        return p.read_text(encoding="utf-8").strip() or _FALLBACK
    except FileNotFoundError:
        return _FALLBACK


def version_code(path: Path | None = None) -> int:
    """``MAJOR*100000 + MINOR`` (BUILD excluded — monotonic for stores)."""
    parts = current(path).split(".")
    major, minor = int(parts[0]), int(parts[1])
    return major * 100000 + minor


def info(path: Path | None = None) -> dict:
    """The full ``version.json`` mirror (productName, packageName, …)."""
    p = path or _VERSION_JSON
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"version": current(path)}
