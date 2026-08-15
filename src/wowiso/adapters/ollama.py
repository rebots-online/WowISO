# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Reference adapter: ollama. §3.9 frozen contract.

Capture: ``systemctl cat ollama`` → override.conf; ``OLLAMA_MODELS`` env from the
service unit; shard dir → blobs tagged ``shard``.
Install (first boot): official install script (clean from repo).
apply_config: write the override, set ``OLLAMA_MODELS``, restore shards as
``ollama:ollama``, ``daemon-reload && enable --now ollama``. **Never copies a
stale binary.**
verify: ``ollama list`` shows the expected models.

A ``runner`` callable (default: ``subprocess.run``) is injected so unit tests can
mock ``systemctl``/``curl`` and assert call order without binaries present.
"""
from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from ..manifest import AppCapture, BlobRef
from .base import RestoreContext, VerifyResult

_DEFAULT_SHARD_DIR = Path("/usr/share/ollama/.ollama/models")
_OVERRIDE_DIR = Path("/etc/systemd/system/ollama.service.d")
_OLLAMA_USER = "ollama"


class OllamaAdapter:
    """Adapter; name = 'ollama'. Reference implementation."""

    name = "ollama"

    def __init__(
        self,
        shard_dir: Path = _DEFAULT_SHARD_DIR,
        override_dir: Path = _OVERRIDE_DIR,
        runner: Callable[[Sequence[str]], subprocess.CompletedProcess] | None = None,
    ) -> None:
        self.shard_dir = shard_dir
        self.override_dir = override_dir
        self._run = runner or (lambda cmd: subprocess.run(cmd, capture_output=True,
                                                          text=True, check=False))

    # -- capture (source box) ------------------------------------------------
    def capture(self, host: object | None = None) -> AppCapture:
        if host is not None:
            raise NotImplementedError("remote capture is the Phase-2 sync seam")
        unit = self._run(["systemctl", "cat", "ollama"]).stdout
        override = _extract_override_conf(unit)
        ollama_models = _extract_env(unit, "OLLAMA_MODELS")
        shards = _capture_shards(self.shard_dir, ollama_models, self._run)
        return AppCapture(
            adapter=self.name,
            data={"override_conf": override, "ollama_models": ollama_models,
                  "shard_dir": str(self.shard_dir)},
            config_blobs=shards,
        )

    # -- install (first boot) -------------------------------------------------
    def install(self, ctx: RestoreContext) -> None:
        # Clean install from the official script — never a copied binary.
        self._run(["bash", "-c",
                   "curl -fsSL https://ollama.com/install.sh | sh"])

    # -- apply_config (first boot) -------------------------------------------
    def apply_config(self, ctx: RestoreContext) -> None:
        cap = _find_app(ctx, self.name)
        if cap is None:
            return
        # OLLAMA_MODELS lives in the override.conf Environment= line (the
        # systemd-correct way); we just write the captured override back.
        self.override_dir.mkdir(parents=True, exist_ok=True)
        (self.override_dir / "override.conf").write_text(
            cap.data.get("override_conf", ""), encoding="utf-8")
        # Restore shards as ollama:ollama (correct ownership), never as a binary.
        for ref in cap.config_blobs:
            src = ctx.store.get(ref.sha256)
            dest = self.shard_dir / Path(ref.store_path).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            self._run(["chown", "-R", f"{_OLLAMA_USER}:{_OLLAMA_USER}", str(dest)])
        self._run(["systemctl", "daemon-reload"])
        self._run(["systemctl", "enable", "--now", "ollama"])

    # -- verify (first boot) --------------------------------------------------
    def verify(self, ctx: RestoreContext) -> VerifyResult:
        expected = {
            Path(ref.store_path).name
            for app in ctx.manifest.apps if app.adapter == self.name
            for ref in app.config_blobs
        }
        listing = self._run(["ollama", "list"]).stdout
        present = {ln.split()[0] for ln in listing.splitlines()[1:] if ln.strip()}
        missing = sorted(expected - present)
        if missing:
            return VerifyResult(ok=False, detail="models missing: " + ", ".join(missing))
        return VerifyResult(ok=True, detail=f"{len(expected)} model(s) present")


def _extract_override_conf(unit_text: str) -> str:
    """Pull the drop-in override body out of `systemctl cat` output."""
    if "[Service]" not in unit_text:
        return ""
    # Everything after the first [Service] header that looks like overrides.
    idx = unit_text.index("[Service]")
    return unit_text[idx:].strip()


def _extract_env(unit_text: str, key: str) -> str:
    m = re.search(rf"^\s*Environment=(?:\"|')?{key}=([^\"'\s]+)", unit_text, re.MULTILINE)
    return m.group(1) if m else os.environ.get(key, "")


def _capture_shards(
    shard_dir: Path, _models_env: str,
    _run: Callable[[Sequence[str]], subprocess.CompletedProcess],
) -> list[BlobRef]:
    """Enumerate shard files into BlobRefs. Needs a BlobStore at capture time.

    The orchestrator (capture CLI) owns the BlobStore; this helper returns refs
    only when a store is wired via the capture path. For the unit-test path it
    returns [] when the dir is absent.
    """
    if not shard_dir.exists():
        return []
    return []  # full shard→blob ingestion happens in the capture CLI (M2.4)


def _find_app(ctx: RestoreContext, name: str) -> AppCapture | None:
    for app in ctx.manifest.apps:
        if app.adapter == name:
            return app
    return None
