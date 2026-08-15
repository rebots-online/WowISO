# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""M5 — render_user_data YAML validity + out_filename version+build scheme."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

from tests.test_manifest import _base
from wowiso.build import out_filename
from wowiso.build.repack import repack_iso
from wowiso.build.seed import render_user_data
from wowiso.build.workdir import WorkDir
from wowiso.manifest import Manifest


def test_render_user_data_structure_and_creds() -> None:
    m = Manifest(**_base())
    text, creds = render_user_data(m)
    assert text.startswith("#cloud-config")
    doc = yaml.safe_load(text)
    ai = doc["autoinstall"]
    assert ai["version"] == 1
    assert ai["interactive-sections"] == []
    assert ai["identity"]["username"] == m.identity.username
    assert ai["identity"]["password"].startswith("$6$")  # SHA-512 crypt
    assert ai["ssh"]["install-server"] is True
    assert ai["storage"]["version"] == 1  # curtin config wired from fs/layout
    assert ai["early-commands"], "guard early-commands must be present"
    assert "runcmd" in ai["user-data"]  # first-boot cloud-config present
    # creds carry the one-time password (not the hash)
    assert "password=" in creds and "$6$" not in creds


def test_out_filename_carries_version_and_build() -> None:
    name = out_filename("dev", "repo", ver="1.1.74918")
    assert re.fullmatch(r"wowiso-v1\.1\.74918-dev-repo\.iso", name)


def test_repack_uses_isohdpfx_for_hybrid_mbr(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """C1 regression: ``-isohybrid-mbr`` must point at isohdpfx.bin, not isolinux.bin.

    isolinux.bin is the full bootloader; the isohybrid MBR slot expects the
    440-byte boot sector (isohdpfx.bin). Subprocess is faked — this asserts
    command construction only.
    """
    root = tmp_path / "tree"
    for rel in ("isolinux/isolinux.bin", "isolinux/isohdpfx.bin", "EFI/boot/efi.img"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x00" * 16)

    seen: dict[str, object] = {}

    def fake_run(cmd: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess:  # type: ignore[type-arg,no-untyped-def]
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("wowiso.build.repack.subprocess.run", fake_run)
    out = repack_iso(WorkDir(root=root, label="WOWISO"), tmp_path / "out.iso")

    assert out == tmp_path / "out.iso"
    cmd = seen["cmd"]  # type: ignore[assignment]
    mbr = cmd[cmd.index("-isohybrid-mbr") + 1]  # type: ignore[index]
    assert Path(mbr).name == "isohdpfx.bin", "hybrid MBR must be the boot sector"
    assert Path(mbr).name != "isolinux.bin"
