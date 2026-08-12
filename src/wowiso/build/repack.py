# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""ISO repack — xorriso mkisofs, hybrid, original volume label preserved. §3.9.

> Full hybrid-boot verification (`file` reports bootable hybrid ISO; label matches
> base) is the M5.4/M8 integration gate — it requires a real Ubuntu 24.04 base ISO
> + syslinux isohdpfx. The command below is constructed from the extracted tree's
> actual boot images; correctness is confirmed at integration time, not here.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .workdir import WorkDir


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


def repack_iso(workdir, out: Path, label: str | None = None) -> Path:  # type: ignore[no-untyped-def]
    from .workdir import WorkDir
    wd: WorkDir = workdir
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    volid = label or wd.label

    isolinux = _find(wd.root, "isolinux/isolinux.bin", "boot/isolinux/isolinux.bin")
    efi_img = _find(wd.root, "EFI/boot/efi.img", "boot/grub/efi.img",
                    "boot/efi.img")

    cmd: list[str] = [
        "xorriso", "-as", "mkisofs",
        "-r", "-V", volid, "-J", "-joliet-long",
        "-o", str(out),
    ]
    if isolinux:
        cmd += ["-b", str(isolinux.relative_to(wd.root)),
                "-c", "isolinux/boot.cat",
                "-boot-load-size", "4", "-boot-info-table"]
    if efi_img:
        cmd += ["-eltorito-alt-boot", "-e", str(efi_img.relative_to(wd.root)),
                "-no-emul-boot", "-isohybrid-gpt-basdat"]
    if isolinux:
        # MBR for isohybrid (BIOS boot); required for true hybrid. May be absent
        # in minimal extracts — xorriso will warn but still produce an ISO.
        cmd += ["-isohybrid-mbr", str(isolinux)]
    cmd.append(str(wd.root))

    subprocess.run(cmd, check=True)
    return out
