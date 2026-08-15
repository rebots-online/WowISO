# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""LIVE-mode squashfs remaster. §3.9 (Phase-2 P2.1)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .workdir import WorkDir


def rebuild_squashfs(workdir: WorkDir, src_root: Path) -> Path:
    """Re-master the live squashfs from a captured root tree (LIVE mode only)."""
    dest = workdir.root / "casper/filesystem.squashfs"
    dest.parent.mkdir(parents=True, exist_ok=True)
    # mksquashfs <src> <dest> -noappend -comp xz
    subprocess.run(
        ["mksquashfs", str(src_root), str(dest), "-noappend", "-comp", "xz",
         "-Xdict-size", "100%"],
        check=True,
    )
    return dest
