# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Disk-identity guard. §3.9 frozen contract.

Renders the autoinstall ``early-commands`` bash that compares the live target
disk id to ``TargetDiskGuard.by_id`` and **aborts the install on mismatch**
(no wrong-disk wipes). ``list_candidate_disks`` enumerates whole disks so the
operator can copy a by-id into a profile.
"""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from .manifest import TargetDiskGuard

_BY_ID_DIR = Path("/dev/disk/by-id")


def _lsblk_one(device: Path) -> tuple[str, str, int]:
    """Return (model, serial, size_bytes) for a device; zeros/empty on failure."""
    try:
        out = subprocess.run(
            ["lsblk", "-bndo", "MODEL,SERIAL,SIZE", str(device)],
            check=True, capture_output=True, text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "", "", 0
    parts = out.stdout.strip().split()
    # SIZE is last; MODEL/SERIAL may contain spaces or be empty.
    if not parts:
        return "", "", 0
    try:
        size = int(parts[-1])
    except ValueError:
        size = 0
    head = parts[:-1]
    model = head[0] if len(head) >= 1 else ""
    serial = head[1] if len(head) >= 2 else ""
    return model, serial, size


def list_candidate_disks() -> list[TargetDiskGuard]:
    """Whole-disk candidates under ``/dev/disk/by-id`` (partitions skipped).

    Returns ``[]`` safely when the by-id directory is absent (non-Linux / CI).
    """
    guards: list[TargetDiskGuard] = []
    if not _BY_ID_DIR.is_dir():
        return guards
    for entry in sorted(_BY_ID_DIR.iterdir()):
        if "-part" in entry.name:  # skip partitions; whole-disk ids only
            continue
        try:
            dev = entry.resolve()
        except OSError:
            continue
        model, serial, size = _lsblk_one(dev)
        if size <= 0:
            continue
        guards.append(
            TargetDiskGuard(by_id=str(entry), model=model, serial=serial, size_bytes=size)
        )
    return guards


def render_early_commands(guard: TargetDiskGuard) -> str:
    """Bash for autoinstall ``early-commands``: abort unless the target disk matches."""
    return (
        "set -eu\n"
        # shlex.quote, NOT repr: a repr that switches to double quotes would let
        # bash command-substitute a hostile by_id inside `bash -c` (root context).
        f"WOWISO_EXPECTED_BY_ID={shlex.quote(guard.by_id)}\n"
        f"WOWISO_EXPECTED_SIZE={guard.size_bytes}\n"
        'if [ ! -e "${WOWISO_EXPECTED_BY_ID}" ]; then\n'
        '  echo "wowiso guard: ABORT — expected disk ${WOWISO_EXPECTED_BY_ID} '
        'not found" >&2\n'
        "  exit 1\n"
        "fi\n"
        '_act="$(readlink -f "${WOWISO_EXPECTED_BY_ID}")"\n'
        '_size="$(lsblk -bndo SIZE "${_act}")"\n'
        'if [ "${_size}" != "${WOWISO_EXPECTED_SIZE}" ]; then\n'
        '  echo "wowiso guard: ABORT — size mismatch (${_size} != '
        '${WOWISO_EXPECTED_SIZE}) on ${WOWISO_EXPECTED_BY_ID}" >&2\n'
        "  exit 1\n"
        "fi\n"
        'echo "wowiso guard: OK (${WOWISO_EXPECTED_BY_ID} -> ${_act})"\n'
    )
