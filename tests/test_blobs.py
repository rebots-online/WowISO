# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""M2.1 — BlobStore dedup + corrupt-blob handling."""
from __future__ import annotations

from pathlib import Path

from wowiso.capture.blobs import BlobStore


def test_put_same_file_twice_dedupes(tmp_path: Path) -> None:
    store = BlobStore(tmp_path / "blobs")
    f = tmp_path / "f.txt"
    f.write_bytes(b"hello-wowiso")
    r1 = store.put(f, "config")
    r2 = store.put(f, "config")
    assert r1.sha256 == r2.sha256
    assert store.has(r1.sha256)
    # exactly one physical blob
    assert len(list((tmp_path / "blobs").rglob("*"))) >= 1
    assert store.get(r1.sha256).read_bytes() == b"hello-wowiso"
    assert r1.size_bytes == len(b"hello-wowiso")


def test_corrupt_blob_verify_returns_false_and_evicts(tmp_path: Path) -> None:
    store = BlobStore(tmp_path / "blobs")
    f = tmp_path / "f.txt"
    f.write_bytes(b"good-bytes")
    ref = store.put(f, "config")
    assert store.verify(ref.sha256) is True
    # corrupt on disk
    store.get(ref.sha256).write_bytes(b"corrupted")
    assert store.verify(ref.sha256) is False
    assert store.has(ref.sha256) is False  # evicted after corruption
