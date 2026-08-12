# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""M1.1 — version.py reads the stamped version.txt (no hand-set constants)."""
from __future__ import annotations

import re

from pathlib import Path

from wowiso import version


def test_current_reads_version_file(tmp_path: Path) -> None:
    vf = tmp_path / "version.txt"
    vf.write_text("1.1.74918\n")
    assert version.current(vf) == "1.1.74918"


def test_current_format_no_leading_zero_major(tmp_path: Path) -> None:
    vf = tmp_path / "version.txt"
    vf.write_text("2.3.00042")  # MAJOR must not begin with 0
    v = version.current(vf)
    assert re.fullmatch(r"[1-9]\d*\.\d+\.\d{1,5}", v)
    assert int(v.split(".")[0]) >= 1


def test_version_code_excludes_build(tmp_path: Path) -> None:
    vf = tmp_path / "version.txt"
    vf.write_text("1.1.74918")
    assert version.version_code(vf) == 1 * 100000 + 1  # BUILD excluded


def test_real_stamped_version_present() -> None:
    # The repo MUST carry a stamped version.txt produced by the stamper.
    v = version.current()
    assert v != version._FALLBACK, "version.txt missing — run scripts/update-version.sh"
    assert int(v.split(".")[0]) >= 1
