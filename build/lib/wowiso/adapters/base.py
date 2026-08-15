# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Adapter contract + registry. §3.9 frozen contract.

An adapter knows how to **capture** an app on the source box and
**install → apply_config → verify** it on the target's first boot. The registry
maps a name (e.g. ``"ollama"``) to an adapter; unknown names fall back to
``GenericAdapter``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from ..capture.blobs import BlobStore
from ..manifest import AppCapture, Manifest


@dataclass
class RestoreContext:
    """Passed to install/apply_config/verify at first boot."""

    manifest: Manifest
    payload_root: Path  # where the /wowiso/ payload is materialised
    store: BlobStore


class VerifyResult(BaseModel):
    ok: bool
    detail: str


@runtime_checkable
class Adapter(Protocol):
    name: str

    def capture(self, host: object | None = None) -> AppCapture: ...
    def install(self, ctx: RestoreContext) -> None: ...
    def apply_config(self, ctx: RestoreContext) -> None: ...
    def verify(self, ctx: RestoreContext) -> VerifyResult: ...


# Seeded by adapters/__init__.py (GenericAdapter + known adapters). ``get`` lazily
# ensures the generic fallback exists to avoid an import cycle (generic imports
# this module).
ADAPTERS: dict[str, Adapter] = {}


def _ensure_generic() -> None:
    if "generic" not in ADAPTERS:
        from .generic import GenericAdapter  # lazy: breaks the import cycle
        ADAPTERS.setdefault("generic", GenericAdapter())


def get(name: str) -> Adapter:
    """Look up an adapter by name; unknown names ⇒ the generic fallback."""
    _ensure_generic()
    return ADAPTERS.get(name, ADAPTERS["generic"])
