# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""M4.2 — build_layout branches + warn_f2fs."""
from __future__ import annotations

from tests.test_manifest import _base  # reuse the manifest fixture
from wowiso.fs.layout import build_layout, warn_f2fs
from wowiso.manifest import Manifest


def _manifest(fs: str) -> Manifest:
    return Manifest(**{**_base(), "filesystem": fs})


def _by_id(config: dict, ident: str) -> dict:
    return next(c for c in config["config"] if c.get("id") == ident)


def test_btrfs_default_root() -> None:
    cfg = build_layout(_manifest("btrfs"))
    assert _by_id(cfg, "root_fs")["fstype"] == "btrfs"
    assert _by_id(cfg, "boot_fs")["fstype"] == "ext4"
    assert _by_id(cfg, "esp_fs")["fstype"] == "fat32"
    assert _by_id(cfg, "disk0")["grub_device"] is True


def test_f2fs_root_with_ext4_boot() -> None:
    cfg = build_layout(_manifest("f2fs"))
    assert _by_id(cfg, "root_fs")["fstype"] == "f2fs"
    assert _by_id(cfg, "boot_fs")["fstype"] == "ext4"


def test_warn_f2fs_only_when_f2fs() -> None:
    assert warn_f2fs(_manifest("btrfs")) == []
    assert len(warn_f2fs(_manifest("f2fs"))) >= 2
