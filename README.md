# WowISO

> **Like WowUSB, but premised on the ISO.** Where WowUSB's unit is the multiboot
> *stick*, WowISO's unit is the *ISO*: one snapshot = one ISO, and a restore point
> is just an ISO you pick in YUMI/Ventoy/iVentoy. Custom Ubuntu 24.04
> installer / live-USB / bare-metal-restore builder — so you never *forget to
> bring stuff*, without doing a naive file-dump restore.

```
wowiso 1.1.74918 — build custom Ubuntu 24.04 autoinstall / live / image artifacts
Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
```

`wowiso` turns the **current** state of an Ubuntu box into one of three
artifacts, each emitted to **ISO**, **USB**, or **Netboot**, so a single large
stick (or a PXE/iVentoy server) carries every restore point you need.

| Mode | What it builds | Source of "the stuff" |
|------|----------------|-----------------------|
| **REPO** | Clean Ubuntu 24.04 install that re-installs your apps from apt/snap/flatpak and re-applies your configs on first boot | package managers + captured config |
| **LIVE** | A bootable live ISO **that is a snapshot of your running desktop** (remastered squashfs) | the live system |
| **IMAGE** | Bare-metal restore of a captured base-system tree **from your HD**, not from package managers | your installed filesystem tree |

> **Kickstart reality:** Ubuntu 24.04 has no classic Red Hat kickstart. We honor
> the *intent* (declarative, hands-off, reproducible) via **Subiquity `autoinstall`**
> + a first-boot cloud-init module — the only automation path Subiquity supports.

## Why not just `dd` a backup?

Because a file dump restores **stale binaries**. `wowiso` installs
apps **clean from their repos**, then re-applies only their *configuration*.
The reference case is **ollama**: install fresh from `ollama.com/install.sh`,
write back the captured `systemctl edit ollama` override + `OLLAMA_MODELS`, then
restore the model shards **as `ollama:ollama`** — never copying a stale
`/usr/local/bin/ollama` into place. Every app with bespoke state gets a
restore adapter; everything else falls back to a generic
`~/.config` restorer.

## Emit targets — "ISO, USB, or Netboot" (every mode → any target)

- **ISO** — hybrid ISO9660+MBR+ESP, original volume label preserved. A true
  drop-in for **YUMI, Ventoy, and iVentoy**; also `dd`/Rufus/balena-writable.
  **One snapshot per ISO** → restore-point selection = picking the ISO.
- **USB** — write a stick directly: either the ISO (dd-style) or a standalone
  **GRUB2 multiboot** stick (GPT/ESP/BIOS_GRUB, F2FS-first — the `wowusb`
  lineage) holding several of your ISOs behind a boot menu.
- **Netboot / iVentoy** — no local media. (a) serve the same ISO via the
  **iVentoy** PXE/iSCSI server (the ISO is already iVentoy-compatible); or
  (b) **iPXE/HTTP internet boot** — the build publishes `vmlinuz`+`initrd`+
  squashfs/payload to an HTTP dir and emits an iPXE menu + a chainloading
  `netboot.iso` (netboot.xyz-style).

## Quickstart

```bash
# 0. install (editable, from repo root)
pipx install -e .

# 1. capture this box into a profile (apt/snap/flatpak lists + .config + adapters)
wowiso capture --profile dev

# 2. pick what to include (desktop-commander-style tree TUI)
wowiso pick --profile dev

# 3. build one snapshot = one ISO  (REPO | LIVE | IMAGE)
sudo wowiso build repo   --profile dev --base ubuntu-24.04.2-desktop-amd64.iso --emit iso
sudo wowiso build live   --profile dev                              --emit iso
sudo wowiso build image  --profile dev --base ubuntu-24.04.2-desktop-amd64.iso --emit iso

# 4. (alt emit targets)
sudo wowiso build repo --profile dev --base … --emit usb   --device /dev/sdX
sudo wowiso build repo --profile dev --base … --emit netboot --http-root /srv/netboot

# 5. drop dist/*.iso onto a Ventoy stick and pick your restore point at boot.
```

### Safety rails
- **Whole-disk auto-install, no encryption, no fsck validation step** — but
  guarded by a **disk-identity check** (`/dev/disk/by-id/...` vs
  `manifest.target_disk`): if the booted machine's disks don't match, the
  installer **aborts before any write**. You tell it which disk is "the right
  one"; it only fires on that one.
- **Filesystem**: **btrfs default** (`@`, `@home` subvols), **f2fs root option**
  where the installer's storage schema permits, `/boot` ext4 for bootloader
  robustness.

## GUI

A **Tauri2** multiplatform GUI (Linux `.deb`/`.rpm`/`AppImage`, Windows
`.exe`/`.msi`, macOS, mobile), **designed via Google Stitch MCP** to be
**platform-adaptive**: GNOME/Adwaita styling on Linux, Fluent/Win11 styling on
Windows — same components, platform-conditional CSS — with the 8 CLAUDE.md
themes (Kinetic / Brutalist / Retro / Neumorphism / Glassmorphism / Y2K /
Cyberpunk / Minimal) layered on top, a Light/Dark/System-Auto toggle, and a
status bar carrying the stamped `MAJOR.MINOR.BUILD` version (bottom-right).

## Version + build scheme

`MAJOR.MINOR.BUILD` (BUILD = epoch-minutes % 100000), derived by
`scripts/update-version.sh` into `version.txt` — never hand-set. `versionCode =
MAJOR*100000 + MINOR`. Build flow: `stamp` → build → on success bump MINOR (so
the tree never falsely attests the just-built version). Embedded in the status
bar, the `File → About` dialog, and the executable filename.

## Reused from `rebots-online/wowusb` (WowUSB-DS9, GPL-3.0)

GRUB2 dual-arch (i386-pc + x86_64-efi) multiboot layout; GPT/ESP(512 MB
FAT32)/BIOS_GRUB(1 MB) partition scheme; F2FS-first payload-fs auto-selection
(F2FS → exFAT → NTFS → BTRFS); the Python CLI + Tauri2 project skeleton. See
`NOTICE` for attribution. WowUSB-DS9 is a USB *writer*, not an ISO assembler —
this project adds the xorriso/squashfs/autoinstall/cloud-init build pipeline on
top of that lineage.

## Roadmap

- **Phase 1** — REPO mode → ISO; ollama + generic adapters; disk-id guard;
  btrfs/f2fs layout; Stitch GUI shell; capture/picker; QEMU smoke test.
- **Phase 2** — **P2P syncer**: content-addressed (sha256) deduped blobs let a
  remote-booted USB replicate just the changed hash-range back to home
  computer(s). The manifest already carries `prev_manifest_sha` as the sync
  chain seam.
- **Phase 3** — LIVE + IMAGE modes to full parity; netboot/iVentoy serving GUI;
  bespoke adapters beyond ollama (docker, tailscale, …).

## Status

**Building.** The design lives in `ARCHITECTURE.md` + `DOCS/ARCHITECTURE/`; the
build plan is `CHECKLIST.md`. The Phase-1 Python core (capture → manifest →
build → ISO pipeline) and the Tauri2 GUI shell (Windows hosts the core in WSL2)
are implemented and tested; Microsoft Store / winget submission readiness is
tracked in `DOCS/SUBMISSION.md` and `CHECKLIST.md` Phase 3.5.

---

Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
Ubuntu is a trademark of Canonical Ltd.; this project is not affiliated with or
endorsed by Canonical. WowUSB-DS9 is licensed GPL-3.0; see `NOTICE`.
