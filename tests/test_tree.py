# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""M2.3 — capture_tree honors includes/excludes + big-tagging."""
from __future__ import annotations

from pathlib import Path

from wowiso.capture.blobs import BlobStore
from wowiso.capture.tree import Rules, capture_tree


def _make_tree(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    (root / ".dotdir").mkdir(parents=True)
    (root / ".dotdir" / "cfg.toml").write_text("a=1")
    (root / "keep.txt").write_text("keep")
    (root / "skip.log").write_text("skip me")
    (root / "big.bin").write_bytes(b"\0" * 300)  # > big_bytes below
    return root


def test_include_exclude_and_big_tag(tmp_path: Path) -> None:
    root = _make_tree(tmp_path)
    store = BlobStore(tmp_path / "blobs")
    rules = Rules(includes=["**"], excludes=["*.log"], big_bytes=256)
    refs = capture_tree([root], store, rules)
    tags = {Path(r.store_path).name for r in refs}  # placeholder; check via sizes
    # skip.log excluded
    assert not any(r.size_bytes == len("skip me") for r in refs)
    # big.bin tagged big
    assert any(r.tag == "big" for r in refs)
    # keep.txt + cfg.toml tagged config
    assert any(r.tag == "config" and r.size_bytes == len("keep") for r in refs)
    assert any(r.size_bytes == len("a=1") for r in refs)
    del tags


def test_single_file_root(tmp_path: Path) -> None:
    f = tmp_path / "single.txt"
    f.write_text("one")
    store = BlobStore(tmp_path / "blobs")
    refs = capture_tree([f], store, Rules())
    assert len(refs) == 1 and refs[0].size_bytes == 3
