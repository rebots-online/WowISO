# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""wowiso CLI (typer). §3.9 entry point: ``wowiso = wowiso.cli:app``.

Command bodies **lazily** import their subsystem module so ``wowiso --help`` and
the command tree are intact even before every Phase-1 module has landed
(milestones are order-independent per the §3 concurrency clause). An unimplemented
command reports the milestone it is waiting on and exits non-zero rather than
crashing on import.
"""
from __future__ import annotations

import typer

from . import version as _version

COPYRIGHT = "Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved."

app = typer.Typer(
    name="wowiso",
    help="Custom Ubuntu 24.04 autoinstall / live / image builder.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
)
build_app = typer.Typer(help="Build artifacts (repo/live/image).")
guard_app = typer.Typer(help="Disk-identity guard.")
app.add_typer(build_app, name="build")
app.add_typer(guard_app, name="guard")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"wowiso {_version.current()}")
        typer.echo(COPYRIGHT)
        raise typer.Exit()


def _unimplemented(milestone: str) -> None:
    typer.echo(
        f"wowiso: `{milestone}` is not implemented yet "
        f"(waiting on CHECKLIST.md {milestone}).",
        err=True,
    )
    raise typer.Exit(code=2)


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", callback=_version_callback, is_eager=True,
        help="Show version+build and exit.",
    ),
) -> None:
    """wowiso — turn this box into portable, bootable artifacts."""


@app.command("version")
def version_cmd() -> None:
    """Print version+build and exit."""
    typer.echo(f"wowiso {_version.current()}")
    typer.echo(COPYRIGHT)


@app.command("capture")
def capture_cmd(
    profile: str = typer.Option(..., help="Profile name to capture into."),
    target_disk_id: str | None = typer.Option(
        None, help="/dev/disk/by-id/… of the intended target disk (recommended)."
    ),
) -> None:
    """Capture this box into a profile (apt/snap/flatpak + tree + adapters)."""
    from .capture import capture_to_profile  # M2.4 — lazy
    m = capture_to_profile(profile, target_disk_id=target_disk_id)
    typer.echo(
        f"captured profile={profile}: {len(m.packages.apt)} apt, "
        f"{len(m.packages.snaps)} snaps, {len(m.packages.flatpaks)} flatpaks, "
        f"{len(m.blobs)} blobs → profiles/{profile}/manifest.json"
    )
    if not target_disk_id:
        typer.echo(
            f"WARNING: defaulted target_disk to {m.target_disk.by_id}; pin it via "
            "--target-disk-id. The disk-id guard aborts on mismatch regardless.",
            err=True,
        )


@app.command("pick")
def pick_cmd(
    profile: str = typer.Option(..., help="Profile whose rules.toml to edit."),
) -> None:
    """Open the tree picker for a profile."""
    _unimplemented("M6")


@build_app.command("repo")
def build_repo_cmd(
    profile: str = typer.Option(...),
    base: str = typer.Option(..., help="Path to a Ubuntu 24.04 base ISO."),
    emit: str = typer.Option("iso", help="iso|usb|netboot"),
    device: str | None = typer.Option(None, help="/dev/sdX (usb emit)."),
    http_root: str | None = typer.Option(None, help="HTTP docroot (netboot emit)."),
) -> None:
    """REPO mode: clean Ubuntu install + first-boot config re-apply → artifact."""
    from pathlib import Path

    from .build import build_repo  # M5 — lazy
    from .manifest import Manifest

    manifest = Manifest.load(Path("profiles") / profile / "manifest.json")
    out = build_repo(
        manifest, Path(base), emit,
        device=Path(device) if device else None,
        http_root=Path(http_root) if http_root else None,
    )
    typer.echo(f"built {out}")
    typer.echo(f"credentials: dist/{profile}-repo-credentials.txt")


@build_app.command("live")
def build_live_cmd(
    profile: str = typer.Option(...),
    emit: str = typer.Option("iso"),
    device: str | None = typer.Option(None),
    http_root: str | None = typer.Option(None),
) -> None:
    """LIVE mode: remaster the running box into a bootable live ISO."""
    del profile, emit, device, http_root
    _unimplemented("P2.1")


@build_app.command("image")
def build_image_cmd(
    profile: str = typer.Option(...),
    base: str = typer.Option(...),
    emit: str = typer.Option("iso"),
    device: str | None = typer.Option(None),
    http_root: str | None = typer.Option(None),
) -> None:
    """IMAGE mode: bare-metal restore of a captured base-system tree."""
    del profile, base, emit, device, http_root
    _unimplemented("P2.2")


@guard_app.command("list-disks")
def guard_list_disks_cmd() -> None:
    """List whole-disk candidates by-id so the operator can pin a target."""
    from .guard import list_candidate_disks  # M4.1 — lazy
    disks = list_candidate_disks()
    if not disks:
        typer.echo("(no whole disks found under /dev/disk/by-id)")
        raise typer.Exit()
    for g in disks:
        typer.echo(f"{g.by_id}\t{g.model}\t{g.serial}\t{g.size_bytes}")


@app.command("netboot")
def netboot_cmd(
    profile: str = typer.Option(...),
    http_root: str = typer.Option(..., help="HTTP docroot to publish into."),
) -> None:
    """Publish a profile's netboot artifacts (iPXE/HTTP)."""
    del profile, http_root
    _unimplemented("P2.4")


@app.command("verify")
def verify_cmd(
    iso: str = typer.Option(..., help="dist/*.iso to boot-test."),
    scratch_disk_id: str | None = typer.Option(None, help="by-id of the scratch disk."),
) -> None:
    """Boot an ISO under QEMU and assert autoinstall + adapter verify() green."""
    del iso, scratch_disk_id
    _unimplemented("M8")
