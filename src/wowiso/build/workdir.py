# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""WorkDir — an extracted ISO tree being assembled. §3.9."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class WorkDir:
    root: Path
    label: str  # original ISO volume label, preserved on repack
