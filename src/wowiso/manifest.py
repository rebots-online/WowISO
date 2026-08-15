# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""SSOT payload manifest (Pydantic v2). §3.9 frozen contract surface.

Every model below is normative: its name, fields, and types are fixed. Coder
agents implement verbatim for interoperability. ``Manifest`` + blobs are
content-addressed and self-describing so the Phase-2 ``sync/`` module can
replicate them by hash range over the ``prev_manifest_sha`` chain.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

MANIFEST_SCHEMA_VERSION: str = "1"


class BlobRef(BaseModel):
    """A content-addressed blob reference (sha256) in the BlobStore."""

    sha256: str
    size_bytes: int
    store_path: str
    owner_uid: int
    owner_gid: int
    mode: str  # octal string, e.g. "0644"
    tag: Literal["config", "big", "shard", "binary"]


class TargetDiskGuard(BaseModel):
    """The disk the operator intends to install onto (by-id + identifying facts)."""

    by_id: str  # /dev/disk/by-id/...
    model: str
    serial: str
    size_bytes: int


class Snap(BaseModel):
    name: str
    channel: str = "stable"
    classic: bool = False


class Flatpak(BaseModel):
    ref: str  # e.g. com.example.App/x86_64/stable
    remote: str


class Packages(BaseModel):
    apt: list[str]
    apt_sources: list[str]  # sources.list.d entries to re-add before install
    snaps: list[Snap]
    flatpaks: list[Flatpak]
    flatpak_remotes: list[str]


class Identity(BaseModel):
    hostname: str
    username: str
    uid: int
    realname: str
    ssh_pubkeys: list[str]


class AppCapture(BaseModel):
    adapter: str  # registry key, e.g. "ollama"
    data: dict  # adapter-specific capture payload
    config_blobs: list[BlobRef]


class Manifest(BaseModel):
    """The top-level payload manifest. One snapshot = one manifest."""

    schema_version: str
    profile: str
    created_at_epoch_s: int  # supplied by caller; no implicit clock inside models
    source_host: str
    ubuntu_release: str  # e.g. "24.04"
    mode: Literal["repo", "live", "image"]
    target_disk: TargetDiskGuard
    filesystem: Literal["btrfs", "f2fs"]
    packages: Packages
    apps: list[AppCapture]
    blobs: list[BlobRef]
    identity: Identity
    adapter_order: list[str]
    prev_manifest_sha: str | None = None  # Phase-2 sync chain

    @classmethod
    def load(cls, path: Path) -> Manifest:
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def dump(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    def chain_sha(self) -> str:
        """sha256 over canonical JSON of self, **excluding** ``prev_manifest_sha``.

        Feeds the append-only sync chain: a manifest's ``prev_manifest_sha`` is the
        ``chain_sha()`` of its predecessor, so the hash must be stable regardless of
        the chain pointer itself.
        """
        data = self.model_dump(mode="json")
        data.pop("prev_manifest_sha", None)
        canon = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canon.encode("utf-8")).hexdigest()
