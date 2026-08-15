# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""M3.1/M3.2/M3.3/M3.4 — registry fallback, generic restore, ollama order, firstboot."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from tests.test_manifest import _base
from wowiso.adapters import ADAPTERS, GenericAdapter, OllamaAdapter, get
from wowiso.adapters.base import RestoreContext
from wowiso.adapters.firstboot import render_firstboot_script
from wowiso.capture.blobs import BlobStore
from wowiso.manifest import AppCapture, Manifest


def test_registry_unknown_falls_back_to_generic() -> None:
    assert isinstance(get("does-not-exist"), GenericAdapter)
    assert get("ollama").name == "ollama"
    assert "generic" in ADAPTERS and "ollama" in ADAPTERS


def test_generic_apply_and_verify_roundtrip(tmp_path: Path) -> None:
    store = BlobStore(tmp_path / "blobs")
    cfg = tmp_path / "app.conf"
    cfg.write_text("k=v")
    ref = store.put(cfg, "config")
    cap = AppCapture(adapter="generic", data={}, config_blobs=[ref])
    m = Manifest(**{**_base(), "apps": [cap], "adapter_order": ["generic"]})
    ctx = RestoreContext(manifest=m, payload_root=tmp_path / "payload", store=store)
    g = GenericAdapter()
    g.install(ctx)
    g.apply_config(ctx)
    assert g.verify(ctx).ok is True


def test_ollama_install_apply_verify_call_order(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    calls: list[list[str]] = []

    def fake_run(cmd):
        calls.append(list(cmd))
        # pretend `ollama list` returns the one expected model
        if cmd[:2] == ["ollama", "list"]:
            return subprocess.CompletedProcess(cmd, 0, "NAME ID SIZE\nllama3 x 1GB\n")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    ada = OllamaAdapter(runner=fake_run,
                        shard_dir=tmp_path / "shards",  # type: ignore[arg-type]
                        override_dir=tmp_path / "override")
    # build a manifest with an ollama app capture referencing one model shard
    cap = AppCapture(adapter="ollama",
                     data={"override_conf": "[Service]\nEnvironment=\"OLLAMA_MODELS=llama3\"",
                           "ollama_models": "llama3", "shard_dir": "/tmp"},
                     config_blobs=[])
    m = Manifest(**{**_base(), "apps": [cap], "adapter_order": ["ollama"]})
    store = BlobStore(Path(m.profile))
    ctx = RestoreContext(manifest=m, payload_root=Path("/tmp/payload"), store=store)
    ada.install(ctx)
    ada.apply_config(ctx)
    result = ada.verify(ctx)
    assert result.ok is True
    # install (curl) runs before daemon-reload/enable runs before ollama list
    joined = [" ".join(c) for c in calls]
    curl_i = next(i for i, s in enumerate(joined) if "ollama.com/install.sh" in s)
    list_i = next(i for i, s in enumerate(joined) if s.startswith("ollama list"))
    assert curl_i < list_i
    # NO stale binary copy: nothing writes /usr/local/bin/ollama
    assert not any("/usr/local/bin/ollama" in s for s in joined)


def test_firstboot_script_logs_ordered_calls(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    m = Manifest(**{**_base(), "adapter_order": ["ollama", "generic"]})
    script = render_firstboot_script(m)
    p = Path("/tmp/_wowiso_fb.sh")
    p.write_text(script)
    os.chmod(p, 0o755)
    env = dict(os.environ, WOWISO_DRY_RUN="1")
    proc = subprocess.run(["bash", str(p)], capture_output=True, text=True, env=env,
                          check=False)
    out = proc.stdout
    assert proc.returncode == 0
    # ordered: ollama install/apply/verify before generic
    assert out.index("ollama") < out.index("generic")
    assert "install   ollama" in out and "verify    generic" in out
