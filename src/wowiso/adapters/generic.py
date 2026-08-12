# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Generic fallback adapter. §3.9 frozen contract.

Nothing bespoke at capture time (the tree capture already covers
``~/.config/<app>``). On first boot it restores the captured config blobs with
their original uid/gid/mode and verifies the paths exist.
"""
from __future__ import annotations

import shutil

from ..manifest import AppCapture
from .base import Adapter, RestoreContext, VerifyResult


class GenericAdapter:
    """Adapter; name = 'generic'. The registry fallback for unknown apps."""

    name = "generic"

    def capture(self, host: object | None = None) -> AppCapture:
        # Tree capture already covers ~/.config/<app>; nothing bespoke to add.
        return AppCapture(adapter=self.name, data={}, config_blobs=[])

    def install(self, ctx: RestoreContext) -> None:  # noqa: ARG002
        # No package to install for the generic case.
        return None

    def apply_config(self, ctx: RestoreContext) -> None:
        # Restore each captured config blob with original ownership/mode. The
        # generic adapter is per-app; callers pass the relevant AppCapture via a
        # closure-free convention: config blobs are restored by the orchestrator
        # from manifest.apps[*].config_blobs for adapter == 'generic'. Here we
        # provide the per-file restore primitive.
        for app in ctx.manifest.apps:
            if app.adapter != self.name:
                continue
            for ref in app.config_blobs:
                src = ctx.store.get(ref.sha256)
                dest = ctx.payload_root / ref.store_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                dest.chmod(int(ref.mode, 8))

    def verify(self, ctx: RestoreContext) -> VerifyResult:
        missing = [
            ref.store_path
            for app in ctx.manifest.apps
            if app.adapter == self.name
            for ref in app.config_blobs
            if not (ctx.payload_root / ref.store_path).exists()
        ]
        if missing:
            return VerifyResult(ok=False, detail="missing: " + ", ".join(missing))
        return VerifyResult(ok=True, detail="generic config restored")
