# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Capture subsystem. §3.9 re-exports.

``Host`` is the thin subprocess-target shim: ``None`` ⇒ capture this local box;
a non-None host is the Phase-2 remote-capture seam (not yet supported).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..manifest import AppCapture, Packages
from .blobs import BlobStore
from .packages import capture_packages
from .tree import Rules, capture_tree

if TYPE_CHECKING:  # avoid runtime import cycle for the type hint
    from ..adapters.base import Adapter

Host = object | None


def capture_app(adapter: "Adapter", host: Host = None) -> AppCapture:
    """Capture one app via its adapter (host=None ⇒ local box)."""
    return adapter.capture(host)


def capture_to_profile(
    profile: str,
    target_disk_id: str | None = None,
    paths: "list[Path] | None" = None,
    mode: str = "repo",
    filesystem: str = "btrfs",
    host: Host = None,
) -> "Manifest":  # type: ignore[name-defined]
    """Full capture → ``profiles/<profile>/manifest.json`` + ``payload/<profile>/``.

    Assembles identity from the local box, captures packages + the default tree
    roots (``~/.bashrc``, ``~/.config``, ``/opt``) + known adapters, and writes a
    valid Manifest. The default target disk is the first whole-disk candidate —
    **the operator should pin it with --target-disk-id**; the disk-id guard
    (guard.py) still aborts the install on mismatch regardless.
    """
    import getpass
    import os
    import pwd
    import socket
    import time
    from pathlib import Path

    from ..adapters import ADAPTERS
    from ..guard import list_candidate_disks
    from ..manifest import Identity, Manifest, TargetDiskGuard

    username = getpass.getuser()
    uid = os.getuid()
    try:
        realname = pwd.getpwuid(uid).pw_gecos.split(",")[0] or username
    except KeyError:
        realname = username
    hostname = socket.gethostname()
    sshdir = Path.home() / ".ssh"
    pubkeys = (
        [p.read_text(encoding="utf-8", errors="replace").strip()
         for p in sshdir.glob("*.pub")]
        if sshdir.is_dir() else []
    )

    disks = list_candidate_disks()
    if target_disk_id:
        target = next(
            (d for d in disks if d.by_id == target_disk_id),
            TargetDiskGuard(by_id=target_disk_id, model="?", serial="?", size_bytes=0),
        )
    elif disks:
        target = disks[0]
    else:
        raise SystemExit(
            "no /dev/disk/by-id candidates found; pass --target-disk-id explicitly"
        )

    packages = capture_packages(host)
    store = BlobStore(Path("payload") / profile / "blobs")
    roots = [p for p in (paths or [Path.home() / ".bashrc",
                                   Path.home() / ".config", Path("/opt")])
             if p.exists()]
    blobs = capture_tree(roots, store, Rules())

    apps = [
        ada.capture(host)
        for ada in ADAPTERS.values()
        if ada.name in ("ollama",)  # known adapters only; generic is the fallback
    ]
    adapter_order = [a.adapter for a in apps]

    manifest = Manifest(
        schema_version="1",
        profile=profile,
        created_at_epoch_s=int(time.time()),
        source_host=hostname,
        ubuntu_release="24.04",
        mode=mode,  # type: ignore[arg-type]
        target_disk=target,
        filesystem=filesystem,  # type: ignore[arg-type]
        packages=packages,
        apps=apps,
        blobs=blobs,
        identity=Identity(hostname=hostname, username=username, uid=uid,
                          realname=realname, ssh_pubkeys=pubkeys),
        adapter_order=adapter_order,
    )
    prof_dir = Path("profiles") / profile
    prof_dir.mkdir(parents=True, exist_ok=True)
    manifest.dump(prof_dir / "manifest.json")
    return manifest


__all__ = [
    "Host",
    "BlobStore",
    "Rules",
    "capture_packages",
    "capture_tree",
    "capture_app",
]
