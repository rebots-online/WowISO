# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""M4.1 — guard.py: rendered early-commands abort on mismatch, proceed on match."""
from __future__ import annotations

import shlex

from wowiso.guard import list_candidate_disks, render_early_commands
from wowiso.manifest import TargetDiskGuard

GUARD = TargetDiskGuard(
    by_id="/dev/disk/by-id/virtio-target", model="V", serial="S", size_bytes=42_000_000_000
)


def test_rendered_script_aborts_on_mismatch() -> None:
    script = render_early_commands(GUARD)
    # abort path is present and fires before the OK line
    assert "exit 1" in script
    assert script.index("not found") < script.index("OK")
    # the expected id + size are baked in
    assert GUARD.by_id in script
    assert str(GUARD.size_bytes) in script


def test_rendered_script_proceeds_on_match(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Execute the rendered guard against a fake by-id that matches in size."""
    import os
    import subprocess

    by_id_dir = tmp_path / "by-id"
    by_id_dir.mkdir()
    target = tmp_path / "node"
    target.write_bytes(b"")
    link = by_id_dir / "virtio-target"
    link.symlink_to(target)
    guard = TargetDiskGuard(
        by_id=str(link), model="V", serial="S", size_bytes=0
    )
    script = render_early_commands(guard)
    # fake lsblk via a shim dir on PATH that prints the expected size
    shim = tmp_path / "shim"
    shim.mkdir()
    (shim / "lsblk").write_text("#!/bin/sh\necho 0\n")
    os.chmod(shim / "lsblk", 0o755)
    env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}")
    # readlink is a coreutils binary; resolve the symlink for the size check
    proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          env=env, check=False)
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout
    # sanity: the quoted id shell-decodes back to the link path
    assert shlex.quote(guard.by_id) in script


def test_rendered_script_quotes_hostile_by_id(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """S1 regression: a by_id with shell metacharacters must never be bash-live.

    Python ``repr`` switches to double quotes when the string contains a single
    quote, and ``$(...)`` is live inside bash double quotes — so a crafted
    manifest by_id could execute as root in early-commands. ``shlex.quote``
    keeps it single-quoted; executing the script must abort (exit 1) with the
    payload inert.
    """
    import subprocess

    hostile = "a'$(touch /tmp/wowiso-pwn)b"
    g = TargetDiskGuard(by_id=hostile, model="x", serial="y", size_bytes=1)
    script = render_early_commands(g)
    # the assignment is the shlex (single-quoted) form, never repr's double form
    assert f"WOWISO_EXPECTED_BY_ID={shlex.quote(hostile)}" in script
    assert f'WOWISO_EXPECTED_BY_ID="{hostile}"' not in script
    # executing the guard must abort cleanly (exit 1) with the payload inert
    marker = tmp_path / "pwned"
    proc = subprocess.run(
        ["bash", "-c", script.replace("/tmp/wowiso-pwn", str(marker))],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 1, proc.stderr
    assert not marker.exists(), "command substitution fired — quoting regressed"


def test_list_candidate_disks_returns_list_safely() -> None:
    # On this host /dev/disk/by-id may or may not exist; the call must not raise.
    out = list_candidate_disks()
    assert isinstance(out, list)
    for g in out:
        assert g.by_id.startswith("/")
