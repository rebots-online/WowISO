# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""File-tree capture (pure-python walk). §3.9 frozen contract.

Walks the given roots, honoring include/exclude globs, and ingests each kept file
into the BlobStore. Files larger than ``rules.big_bytes`` are tagged ``big`` (so a
profile can opt them out); everything else is tagged ``config``.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path

from pydantic import BaseModel

from ..manifest import BlobRef
from .blobs import BlobStore


class Rules(BaseModel):
    includes: list[str] = ["**"]
    excludes: list[str] = []
    big_bytes: int = 256 * 1024 * 1024


def _excluded(path: Path, rules: Rules) -> bool:
    name = str(path)
    return any(fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(path.name, pat)
               for pat in rules.excludes)


def _included(path: Path, rules: Rules) -> bool:
    if not rules.includes:
        return True
    name = str(path)
    return any(fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(path.name, pat)
               for pat in rules.includes)


def capture_tree(paths: list[Path], store: BlobStore, rules: Rules) -> list[BlobRef]:
    """Walk ``paths`` → deduped BlobRefs in ``store``, honoring rules."""
    refs: list[BlobRef] = []
    for root in paths:
        root = Path(root).expanduser()
        if root.is_file():
            if _excluded(root, rules) or not _included(root, rules):
                continue
            refs.append(store.put(root, _tag(root, rules)))
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.is_symlink():
                continue
            if _excluded(p, rules) or not _included(p, rules):
                continue
            try:
                refs.append(store.put(p, _tag(p, rules)))
            except (PermissionError, OSError):
                continue  # unreadable file (e.g. root-owned under /opt) — skip
    return refs


def _tag(path: Path, rules: Rules) -> str:
    return "big" if path.stat().st_size > rules.big_bytes else "config"
