# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""ISO repack — xorriso mkisofs, hybrid, original volume label preserved. §3.9.

> Full hybrid-boot verification (`file` reports bootable hybrid ISO; label matches
> base) is the M5.4/M8 integration gate — it requires a real Ubuntu 24.04 base ISO
> + syslinux isohdpfx. The command below is constructed from the extracted tree's
> actual boot images; correctness is confirmed at integration time, not here.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .workdir import WorkDir

# isohdpfx.bin is the 440-byte MBR boot sector syslinux ships for isohybrid —
# NOT isolinux.bin (the full bootloader). Without it the ISO is El Torito-only
# and a raw `dd` write will not BIOS-boot. Searched in the extracted tree first,
# then common host syslinux install paths.
_ISOHDPFX_TREE = (
    "isolinux/isohdpfx.bin",
    "boot/isolinux/isohdpfx.bin",
    "boot/syslinux/isohdpfx.bin",
)
_ISOHDPFX_HOST = (
    "/usr/lib/ISOLINUX/isohdpfx.bin",   # Debian/Ubuntu (syslinux-common)
    "/usr/lib/syslinux/isohdpfx.bin",
    "/usr/share/syslinux/isohdpfx.bin",
)


def _find(root: Path, *candidates: str) -> Path | None:
    for c in candidates:
        p = root / c
        if p.exists():
            return p
    # last-resort glob
    for c in candidates:
        hits = list(root.rglob(Path(c).name))
        if hits:
            return hits[0]
    return None


def _find_isohdpfx(root: Path) -> Path | None:
    """Locate the isohybrid MBR sector: extracted tree first, then the host."""
    hit = _find(root, *_ISOHDPFX_TREE)
    if hit:
        return hit
    for host in _ISOHDPFX_HOST:
        p = Path(host)
        if p.is_file():
            return p
    return None


def repack_iso(workdir: WorkDir, out: Path, label: str | None = None) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    volid = label or workdir.label

    isolinux = _find(workdir.root, "isolinux/isolinux.bin", "boot/isolinux/isolinux.bin")
    efi_img = _find(workdir.root, "EFI/boot/efi.img", "boot/grub/efi.img",
                    "boot/efi.img")
    isohdpfx = _find_isohdpfx(workdir.root)

    cmd: list[str] = [
        "xorriso", "-as", "mkisofs",
        "-r", "-V", volid, "-J", "-joliet-long",
        "-o", str(out),
    ]
    if isolinux:
        cmd += ["-b", str(isolinux.relative_to(workdir.root)),
                "-c", "isolinux/boot.cat",
                "-boot-load-size", "4", "-boot-info-table"]
    if efi_img:
        cmd += ["-eltorito-alt-boot", "-e", str(efi_img.relative_to(workdir.root)),
                "-no-emul-boot", "-isohybrid-gpt-basdat"]
    if isohdpfx:
        # The true-hybrid MBR: BIOS boots the raw image after dd/Rufus/balena.
        cmd += ["-isohybrid-mbr", str(isohdpfx)]
    else:
        print(
            "wowiso: warning: isohdpfx.bin not found (extracted tree or host "
            "syslinux) — the ISO will be El Torito-only, NOT BIOS-hybrid (dd).",
            file=sys.stderr,
        )
    cmd.append(str(workdir.root))

    subprocess.run(cmd, check=True)
    return out
