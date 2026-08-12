# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""Seed injection — the autoinstall user-data + nocloud meta-data. §3.9.

``render_user_data`` is pure (YAML) and testable; ``inject_seed`` writes the seed
into a WorkDir and stages the first-boot restore script + manifest copy.
"""
from __future__ import annotations

import secrets
import shlex
import string
import subprocess
from pathlib import Path

import yaml

from ..adapters.firstboot import render_firstboot_script
from ..fs.layout import build_layout
from ..guard import render_early_commands
from ..manifest import Manifest


def _rand_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(18))


def _hash_password(pw: str) -> str:
    """SHA-512 ($6$) crypt hash via openssl (portable; `crypt` was removed in py3.13)."""
    out = subprocess.run(
        ["openssl", "passwd", "-6", pw], check=True, capture_output=True, text=True
    )
    return out.stdout.strip()


def render_user_data(manifest: Manifest) -> tuple[str, str]:
    """Return ``(autoinstall_user_data_yaml, credentials_text)``.

    A random one-time password is generated (Identity carries no password in the
    manifest by design); its plaintext is returned so the operator can log in and
    is also written next to the emitted ISO.
    """
    password = _rand_password()
    pw_hash = _hash_password(password)
    early = render_early_commands(manifest.target_disk)

    doc = {
        "autoinstall": {
            "version": 1,
            "interactive-sections": [],
            "locale": "en_US.UTF-8",
            "keyboard": {"layout": "us"},
            "identity": {
                "realname": manifest.identity.realname,
                "username": manifest.identity.username,
                "hostname": manifest.identity.hostname,
                "password": pw_hash,
            },
            "ssh": {
                "install-server": True,
                "authorized-keys": list(manifest.identity.ssh_pubkeys),
            },
            "storage": build_layout(manifest),
            "early-commands": ["bash -c " + shlex.quote(early)],
            "late-commands": [
                "mkdir -p /target/wowiso",
                "cp -a /cdrom/wowiso/. /target/wowiso/",
            ],
            # First-boot cloud-config for the *installed* system:
            "user-data": {
                "runcmd": [
                    "chmod +x /wowiso/wowiso-restore",
                    "/wowiso/wowiso-restore",
                ]
            },
        }
    }
    yaml_text = "#cloud-config\n" + yaml.safe_dump(doc, sort_keys=False)
    creds = (
        f"wowiso profile={manifest.profile} mode={manifest.mode}\n"
        f"user={manifest.identity.username} password={password}\n"
        f"(one-time; change on first login)\n"
    )
    return yaml_text, creds


def inject_seed(workdir, manifest: Manifest) -> str:  # type: ignore[no-untyped-def]
    """Write nocloud seed + restore script + manifest copy into ``workdir``.

    Returns the credentials text (caller writes it beside the emitted ISO).
    """
    from .workdir import WorkDir  # local import to avoid cycle in type checkers
    wd: WorkDir = workdir
    seed_dir = wd.root / "wowiso" / "seed"
    seed_dir.mkdir(parents=True, exist_ok=True)

    yaml_text, creds = render_user_data(manifest)
    (seed_dir / "user-data").write_text(yaml_text, encoding="utf-8")
    (seed_dir / "meta-data").write_text(
        f"instance-id: wowiso-{manifest.profile}\n"
        f"local-hostname: {manifest.identity.hostname}\n",
        encoding="utf-8",
    )

    # first-boot restore script + manifest copy alongside the payload
    wowiso = wd.root / "wowiso"
    wowiso.mkdir(parents=True, exist_ok=True)
    (wowiso / "wowiso-restore").write_text(
        render_firstboot_script(manifest), encoding="utf-8")
    (wowiso / "manifest.json").write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8")
    return creds
