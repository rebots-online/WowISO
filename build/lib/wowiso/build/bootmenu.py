# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Boot-menu patching — append the autoinstall cmdline. §3.9.

Best-effort, idempotent: adds the ``autoinstall ds=nocloud-net;s=/wowiso/seed/``
suffix to the default boot entries in ``grub/grub.cfg`` and ``isolinux/txt.cfg``
when those files exist in the extracted tree. Install/Live/Rescue labels are left
to the base ISO's existing menu; we only inject the autoinstall switch.
"""
from __future__ import annotations

from pathlib import Path

from .workdir import WorkDir

_CMDLINE_SUFFIX = " autoinstall ds=nocloud-net;s=/wowiso/seed/"
_MARKER = "wowiso-autoinstall-patched"


def _patch(path: Path) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if _MARKER in text:
        return
    # Append the suffix to every `linux` / `append` line that lacks it.
    out_lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("linux", "append")) and "autoinstall" not in line:
            out_lines.append(line.rstrip() + _CMDLINE_SUFFIX)
        else:
            out_lines.append(line)
    out_lines.append(f"# {_MARKER}")
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def edit_boot_menu(workdir: WorkDir) -> None:
    _patch(workdir.root / "boot/grub/grub.cfg")
    _patch(workdir.root / "boot/grub/loopback.cfg")
    _patch(workdir.root / "isolinux/txt.cfg")
