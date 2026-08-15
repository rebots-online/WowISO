# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Netboot HTTP publish. §3.9 (Phase-2 P2.4).

Publishes ``vmlinuz`` + ``initrd`` + squashfs/payload out of a WorkDir into an
HTTP docroot, netboot.xyz-style, alongside the rendered iPXE menu.
"""
from __future__ import annotations

from pathlib import Path

from ..build.workdir import WorkDir


def publish_http(workdir: WorkDir, docroot: Path) -> None:
    """Publish the netboot artifacts under ``docroot`` (P2.4)."""
    raise NotImplementedError("netboot publish is P2.4 (iPXE/HTTP + iVentoy serving).")
