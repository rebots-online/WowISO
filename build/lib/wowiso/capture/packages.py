# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Package-source capture. §3.9 frozen contract.

Captures the **source of truth** for what to re-install on the target:
``apt-mark showmanual``, ``snap list``, ``flatpak list --app``, plus the apt
sources and flatpak remotes needed to re-add them before install. Each tool is
guarded: if the binary is absent (e.g. flatpak not installed), that section is
empty rather than fatal — so capture runs on any box without error.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from ..manifest import Flatpak, Packages, Snap

_APT_SOURCES_DIR = Path("/etc/apt/sources.list.d")


def _run(cmd: list[str], host: object | None) -> subprocess.CompletedProcess[str]:
    """Run a command locally (host is accepted for the Phase-2 remote seam)."""
    if host is not None:
        raise NotImplementedError("remote-host capture is the Phase-2 sync seam")
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _apt(host: object | None) -> tuple[list[str], list[str]]:
    pkg = _run(["apt-mark", "showmanual"], host)
    packages = [ln.strip() for ln in pkg.stdout.splitlines() if ln.strip()]
    sources: list[str] = []
    if _APT_SOURCES_DIR.is_dir():
        for entry in sorted(_APT_SOURCES_DIR.glob("*.list")):
            sources.append(entry.read_text(encoding="utf-8", errors="replace"))
    return packages, sources


def _snaps(host: object | None) -> list[Snap]:
    res = _run(["snap", "list"], host)
    snaps: list[Snap] = []
    lines = res.stdout.splitlines()
    if res.returncode != 0 or len(lines) < 2:
        return snaps
    for ln in lines[1:]:
        cols = ln.split()
        if len(cols) < 6:
            continue
        name, _ver, _rev, tracking, _publisher, notes = cols[:6]
        snaps.append(
            Snap(name=name, channel=tracking or "stable", classic="classic" in notes)
        )
    return snaps


def _flatpaks(host: object | None) -> tuple[list[Flatpak], list[str]]:
    res = _run(
        ["flatpak", "list", "--app",
         "--columns=application,origin,branch,installation"],
        host,
    )
    flatpaks: list[Flatpak] = []
    for ln in res.stdout.splitlines():
        cols = ln.split("\t")
        if len(cols) < 4 or not cols[0]:
            continue
        application, origin, branch, _inst = cols[:4]
        flatpaks.append(Flatpak(ref=f"{application}/{branch}", remote=origin))
    remotes_res = _run(["flatpak", "remotes"], host)
    remotes = [ln.split("\t")[0] for ln in remotes_res.stdout.splitlines() if ln.strip()]
    return flatpaks, remotes


def capture_packages(host: object | None = None) -> Packages:
    """Capture apt/snap/flatpak + their sources/remotes from this box (host=None)."""
    apt, apt_sources = _apt(host)
    snaps = _snaps(host)
    flatpaks, flatpak_remotes = _flatpaks(host)
    return Packages(
        apt=apt,
        apt_sources=apt_sources,
        snaps=snaps,
        flatpaks=flatpaks,
        flatpak_remotes=flatpak_remotes,
    )
