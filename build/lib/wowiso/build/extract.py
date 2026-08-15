# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Base-ISO extraction (xorriso). §3.9. Cached by source sha256."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .workdir import WorkDir

_CACHE = Path("cache/base")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _volume_label(iso: Path) -> str:
    """Read the ISO9660 volume label via xorriso."""
    out = subprocess.run(
        ["xorriso", "-indev", str(iso), "-report_system_area", "plain", "--"],
        check=False, capture_output=True, text=True,
    )
    # Fall back to a volid inquiry.
    vid = subprocess.run(
        ["xorriso", "-indev", str(iso), "-print", "ISO9660:Volid", "--"],
        check=False, capture_output=True, text=True,
    )
    label = (vid.stdout or out.stdout).strip().splitlines()
    return label[0] if label else f"WOWISO-{iso.stem}"


def extract_base_iso(iso_path: Path) -> WorkDir:
    """Extract a base ISO into a sha256-keyed cache dir; return its WorkDir."""
    iso_path = Path(iso_path)
    sha = _sha256(iso_path)
    dest = _CACHE / sha
    if not dest.exists():
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["xorriso", "-osirrox", "on", "-indev", str(iso_path),
             "-extract", "/", str(dest)],
            check=True,
        )
    return WorkDir(root=dest, label=_volume_label(iso_path))
