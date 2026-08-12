# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Filesystem layout builder. §3.9 frozen contract.

Emits a curtin v1 ``storage`` config for Subiquity autoinstall: single largest
disk, GPT, BIOS_GRUB(1 MB) + ESP(512 MB FAT32) + ``/boot``(1 GB ext4) + root on
``btrfs`` (default) or ``f2fs`` (option). Subiquity auto-creates the ``@`` and
``@home`` btrfs subvolumes when the root is btrfs.

> NOTE: full JSON-schema validation against the live Subiquity ``storage`` schema
> is the remaining M4.2 acceptance slice (schema not vendored in-repo yet); the
> structure here is a standard curtin v1 config.
"""
from __future__ import annotations

from ..manifest import Manifest

_MIB = 1024 * 1024


def build_layout(manifest: Manifest) -> dict:
    """Return a curtin v1 ``storage`` config dict for the manifest's filesystem."""
    root_fstype = "btrfs" if manifest.filesystem == "btrfs" else "f2fs"
    return {
        "version": 1,
        "config": [
            {"id": "disk0", "type": "disk", "ptable": "gpt",
             "match": {"size": "largest"}, "grub_device": True},
            {"id": "bios_grub", "type": "partition", "device": "disk0",
             "size": 1 * _MIB, "flag": "bios_grub"},
            {"id": "esp_part", "type": "partition", "device": "disk0",
             "size": 512 * _MIB, "flag": "boot"},
            {"id": "esp_fs", "type": "format", "fstype": "fat32",
             "volume": "esp_part", "label": "EFI"},
            {"id": "boot_part", "type": "partition", "device": "disk0",
             "size": 1024 * _MIB},
            {"id": "boot_fs", "type": "format", "fstype": "ext4",
             "volume": "boot_part", "label": "boot"},
            {"id": "root_part", "type": "partition", "device": "disk0", "size": -1},
            {"id": "root_fs", "type": "format", "fstype": root_fstype,
             "volume": "root_part", "label": "root"},
            {"id": "mnt_root", "type": "mount", "device": "root_fs", "path": "/"},
            {"id": "mnt_boot", "type": "mount", "device": "boot_fs", "path": "/boot"},
            {"id": "mnt_esp", "type": "mount", "device": "esp_fs", "path": "/boot/efi"},
        ],
    }


def warn_f2fs(manifest: Manifest) -> list[str]:
    """Pre-flight caveats when the operator chose an f2fs root.

    f2fs root is solid on most modern kernels but has rough corners (some
    backup/restore tooling, certain RAID/encryption combos). Surface them so the
    choice is informed. Empty list for btrfs.
    """
    if manifest.filesystem != "f2fs":
        return []
    return [
        "f2fs root: some block-level backup tools (fsarchiver/partclone) have "
        "limited f2fs support — IMAGE-mode captures may fall back to file-level.",
        "f2fs root: verify your bootloader/firmware combo; /boot is ext4 here to "
        "keep GRUB robust regardless of root fstype.",
        "f2fs root: TRIM/discard behavior differs from ext4; confirm discard is "
        "enabled post-install on SSD/NVMe targets.",
    ]
