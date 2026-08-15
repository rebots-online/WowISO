# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""USB emit. §3.9. GRUB2 multiboot (GPT/ESP/BIOS_GRUB, F2FS-first) is P2.3."""
from __future__ import annotations

from pathlib import Path


def write_usb(iso: Path, device: Path, multiboot: bool = False) -> None:
    """Write an ISO to a USB device.

    ``multiboot=False``: dd the ISO to ``device`` (destructive — whole disk).
    ``multiboot=True``: standalone GRUB2 multiboot stick layout — **P2.3**.
    """
    raise NotImplementedError(
        "USB emit is P2.3 (GRUB2 multiboot layout, GPT/ESP/BIOS_GRUB, F2FS-first). "
        "ISO emit via `build repo --emit iso` is the M5 deliverable."
    )
