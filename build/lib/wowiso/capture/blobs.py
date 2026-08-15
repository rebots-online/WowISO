# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Content-addressed, deduped blob store. §3.9 frozen contract.

Files are stored under ``<root>/xx/yy/<sha256>`` (two-level shard by the first
four hex chars) and deduped by sha256 across profiles. ``verify`` re-hashes on
disk; a corrupt blob is deleted and ``has`` returns False afterwards.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from ..manifest import BlobRef

_HASHBUF = 1024 * 1024


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(_HASHBUF), b""):
            h.update(chunk)
    return h.hexdigest()


class BlobStore:
    """A content-addressed store rooted at ``payload/<profile>/blobs``."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, sha256: str) -> Path:
        return self.root / sha256[:2] / sha256[2:4] / sha256

    def put(self, path: Path, tag: str) -> BlobRef:
        """Ingest ``path``; returns a BlobRef preserving its uid/gid/mode. Deduped."""
        sha = _sha256_file(path)
        dest = self._path(sha)
        st = path.stat()
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        return BlobRef(
            sha256=sha,
            size_bytes=st.st_size,
            store_path=str(dest.relative_to(self.root)),
            owner_uid=st.st_uid,
            owner_gid=st.st_gid,
            mode=format(st.st_mode & 0o7777, "04o"),
            tag=tag,  # type: ignore[arg-type]
        )

    def get(self, sha256: str) -> Path:
        """Absolute path to the stored blob; raises KeyError if absent."""
        p = self._path(sha256)
        if not p.exists():
            raise KeyError(sha256)
        return p

    def has(self, sha256: str) -> bool:
        return self._path(sha256).exists()

    def verify(self, sha256: str) -> bool:
        """Re-hash on disk. Corrupt blobs are deleted; returns False then."""
        p = self._path(sha256)
        if not p.exists():
            return False
        if _sha256_file(p) != sha256:
            p.unlink(missing_ok=True)
            return False
        return True
