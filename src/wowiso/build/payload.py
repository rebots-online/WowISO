# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Payload injection — rsync a profile's payload into the WorkDir. §3.9."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .workdir import WorkDir

_PAYLOAD = Path("payload")


def inject_payload(workdir: WorkDir, profile: str) -> None:
    """rsync ``payload/<profile>/`` under ``<workdir.root>/wowiso/``."""
    src = _PAYLOAD / profile
    dest = workdir.root / "wowiso"
    dest.mkdir(parents=True, exist_ok=True)
    if shutil.which("rsync"):
        subprocess.run(
            ["rsync", "-a", f"{src}/", f"{dest}/"],
            check=True,
        )
    else:  # graceful fallback where rsync is absent
        subprocess.run(["cp", "-a", f"{src}/.", str(dest)], check=True)
