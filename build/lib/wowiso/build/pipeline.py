# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Build pass-2 orchestrators. §3.9. The ONLY build/ file that imports the steps.

``build_repo`` is the M5 end-to-end path (manifest + base ISO → bootable ISO).
``build_live`` / ``build_image`` are Phase-2 modes (P2.1 / P2.2).
"""
from __future__ import annotations

from pathlib import Path

from .. import version as _version
from ..manifest import Manifest
from .bootmenu import edit_boot_menu
from .extract import extract_base_iso
from .payload import inject_payload
from .repack import repack_iso
from .seed import inject_seed

_DIST = Path("dist")


def out_filename(profile: str, mode: str, ver: str | None = None, ext: str = "iso") -> str:
    """Slug-first (CC12): ``wowiso-v<version>-<profile>-<mode>.<ext>``."""
    return f"wowiso-v{ver or _version.current()}-{profile}-{mode}.{ext}"


def build_repo(
    manifest: Manifest,
    base_iso: Path,
    emit: str = "iso",
    *,
    device: Path | None = None,
    http_root: Path | None = None,
) -> Path:
    """REPO mode end-to-end → artifact (ISO primary; USB/Netboot are P2)."""
    wd = extract_base_iso(Path(base_iso))
    inject_payload(wd, manifest.profile)
    creds = inject_seed(wd, manifest)
    edit_boot_menu(wd)

    _DIST.mkdir(exist_ok=True)
    (Path("cache")).mkdir(exist_ok=True)
    out = _DIST / out_filename(manifest.profile, "repo")
    creds_path = _DIST / out_filename(manifest.profile, "repo", ext="credentials.txt")
    creds_path.write_text(creds, encoding="utf-8")
    creds_path.chmod(0o600)  # carries the one-time plaintext password (S3)

    if emit == "iso":
        repack_iso(wd, out, wd.label)
    elif emit == "usb":
        if device is None:
            raise ValueError("--emit usb requires --device /dev/sdX")
        from .usb import write_usb  # P2.3
        repack_iso(wd, out, wd.label)
        write_usb(out, device, multiboot=True)
    elif emit == "netboot":
        if http_root is None:
            raise ValueError("--emit netboot requires --http-root DIR")
        from ..netboot import publish_http  # P2.4 — lazy
        repack_iso(wd, out, wd.label)
        publish_http(wd, http_root)
    else:
        raise ValueError(f"unknown emit target: {emit}")
    return out


def build_live(manifest: Manifest, emit: str = "iso", *,
               device: Path | None = None, http_root: Path | None = None) -> Path:
    raise NotImplementedError("LIVE mode is P2.1 (rebuild_squashfs remaster).")


def build_image(manifest: Manifest, base_iso: Path, emit: str = "iso", *,
                device: Path | None = None, http_root: Path | None = None) -> Path:
    raise NotImplementedError("IMAGE mode is P2.2 (bare-metal tree restore).")
