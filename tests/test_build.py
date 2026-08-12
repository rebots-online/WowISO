# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""M5 — render_user_data YAML validity + out_filename version+build scheme."""
from __future__ import annotations

import re

import yaml

from wowiso.build import out_filename
from wowiso.build.seed import render_user_data
from wowiso.manifest import Manifest

from tests.test_manifest import _base


def test_render_user_data_structure_and_creds() -> None:
    m = Manifest(**_base())
    text, creds = render_user_data(m)
    assert text.startswith("#cloud-config")
    doc = yaml.safe_load(text)
    ai = doc["autoinstall"]
    assert ai["version"] == 1
    assert ai["interactive-sections"] == []
    assert ai["identity"]["username"] == m.identity.username
    assert ai["identity"]["password"].startswith("$6$")  # SHA-512 crypt
    assert ai["ssh"]["install-server"] is True
    assert ai["storage"]["version"] == 1  # curtin config wired from fs/layout
    assert ai["early-commands"], "guard early-commands must be present"
    assert "runcmd" in ai["user-data"]  # first-boot cloud-config present
    # creds carry the one-time password (not the hash)
    assert "password=" in creds and "$6$" not in creds


def test_out_filename_carries_version_and_build() -> None:
    name = out_filename("dev", "repo", ver="1.1.74918")
    assert re.fullmatch(r"wowiso-v1\.1\.74918-dev-repo\.iso", name)
