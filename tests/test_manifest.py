# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""M1.2 — Manifest round-trip + enum rejection + chain_sha stability."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from wowiso.manifest import (
    MANIFEST_SCHEMA_VERSION,
    AppCapture,
    BlobRef,
    Flatpak,
    Identity,
    Manifest,
    Packages,
    Snap,
    TargetDiskGuard,
)


def _base() -> dict:
    return dict(
        schema_version=MANIFEST_SCHEMA_VERSION,
        profile="dev",
        created_at_epoch_s=1_700_000_000,
        source_host="box",
        ubuntu_release="24.04",
        mode="repo",
        target_disk=TargetDiskGuard(
            by_id="/dev/disk/by-id/virtio-disk", model="V", serial="S", size_bytes=1
        ),
        filesystem="btrfs",
        packages=Packages(apt=["git"], apt_sources=[], snaps=[Snap(name="go")],
                          flatpaks=[Flatpak(ref="com.example.App/x86_64/stable", remote="flathub")],
                          flatpak_remotes=["flathub"]),
        apps=[AppCapture(adapter="ollama", data={"models": ["llama3"]}, config_blobs=[])],
        blobs=[BlobRef(sha256="ab" * 32, size_bytes=10, store_path="x", owner_uid=0,
                       owner_gid=0, mode="0644", tag="config")],
        identity=Identity(hostname="h", username="u", uid=1000, realname="U", ssh_pubkeys=[]),
        adapter_order=["ollama"],
    )


def test_roundtrip(tmp_path: Path) -> None:
    m = Manifest(**_base())
    p = tmp_path / "manifest.json"
    m.dump(p)
    assert Manifest.load(p) == m


def test_rejects_bad_mode_enum() -> None:
    with pytest.raises(ValidationError):
        Manifest(**{**_base(), "mode": "nonsense"})


def test_rejects_bad_blob_tag_enum() -> None:
    # Corrupt at the serialized layer so Manifest-level validation catches it
    # (constructing BlobRef with a bad tag raises before Manifest() is reached).
    m = Manifest(**_base())
    dumped = m.model_dump(mode="json")
    dumped["blobs"][0]["tag"] = "not-a-tag"
    with pytest.raises(ValidationError):
        Manifest.model_validate(dumped)


def test_chain_sha_excludes_prev_and_is_stable() -> None:
    m = Manifest(**_base())
    sha = m.chain_sha()
    assert len(sha) == 64  # sha256 hex
    # pointing at a predecessor must not change this manifest's own hash
    m2 = m.model_copy(update={"prev_manifest_sha": "deadbeef"})
    assert m2.chain_sha() == sha
