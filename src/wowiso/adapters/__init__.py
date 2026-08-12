# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Adapters subsystem. §3.9 re-exports + registry seeding."""
from __future__ import annotations

from .base import ADAPTERS, Adapter, RestoreContext, VerifyResult, get
from .firstboot import render_firstboot_script
from .generic import GenericAdapter
from .ollama import OllamaAdapter

# Seed the registry with the fallback + the reference adapter.
ADAPTERS.setdefault("generic", GenericAdapter())
ADAPTERS.setdefault("ollama", OllamaAdapter())

__all__ = [
    "ADAPTERS",
    "Adapter",
    "RestoreContext",
    "VerifyResult",
    "GenericAdapter",
    "OllamaAdapter",
    "render_firstboot_script",
    "get",
]
