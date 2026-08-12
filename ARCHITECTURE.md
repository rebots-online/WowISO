# ARCHITECTURE — WowISO

> **Agent role**: this document is the system design. Coder agents follow
> `CHECKLIST.md` and the representations in `DOCS/ARCHITECTURE/`. If the design
> must change, HALT, return to architect mode, update this file + diagrams +
> checklist, then resume coding.

```
Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
```

## 1. Purpose

Turn the *current* Ubuntu machine into portable, bootable artifacts so the
operator never "forgets to bring stuff," while avoiding a naive file-dump
restore. Three **modes** × three **emit targets**:

| Mode   | What it builds                                                         |
|--------|------------------------------------------------------------------------|
| REPO   | Clean Ubuntu 24.04 install from apt/snap/flatpak + first-boot config re-apply |
| LIVE   | A bootable live ISO whose squashfs *is* a snapshot of the running box  |
| IMAGE  | Bare-metal restore of a captured base-system tree (no package managers) |

| Emit target | Consumed by                                                      |
|-------------|------------------------------------------------------------------|
| **ISO**     | YUMI / Ventoy / iVentoy, or `dd`/Rufus/balena to any stick      |
| **USB**     | Direct write, or standalone GRUB2 multiboot stick (wowusb lineage) |
| **Netboot** | iVentoy PXE/iSCSI serve, or standalone iPXE/HTTP internet boot   |

**One snapshot = one ISO/image.** Selecting a restore point = choosing the ISO
in YUMI/Ventoy/iVentoy.

> Ubuntu 24.04 has no classic Red Hat kickstart. We honor the *kickstart intent*
> — declarative, hands-off, reproducible — via **Subiquity `autoinstall`**
> (`user-data`) + a first-boot **cloud-init** module. This is the only
> automation path Subiquity supports.

## 2. Component map

```
                 ┌──────────────────────────────────────────────────────┐
   operator ───► │  GUI (Tauri2, Stitch-designed, GNOME/Adwaita+Fluent) │
                 │  + TUI picker (Textual, gum/fzf fallback)             │
                 └───────────────┬──────────────────────────────────────┘
                                 │ (same commands)
                 ┌───────────────▼───────────────┐
                 │           cli.py (typer)       │
                 └───┬──────┬──────┬──────┬──────┘
        capture/     │      │      │      │       netboot/
   apt/snap/flatpak  │   picker/   │   build/      iPXE+HTTP, iVentoy
   + adapters ──► manifest.json + payload/<profile>/ ──► ISO/USB/Netboot
                     │             │
                  guard.py      fs/ (btrfs|f2fs layout)
                  (disk-id)     adapters/ (ollama, …) run in cloud-init
```

## 3. Subsystems (module contracts)

> Path prefix: `src/wowiso/`. Names here are the canonical class/function
> names coder agents must implement verbatim for interoperability.
>
> **Concurrency model — dependency order is architecturally irrelevant.**
> §3.9 (Entity registry) is the **frozen contract surface**: every entity's name,
> file, and signature is fixed there. Each `CHECKLIST.md` milestone implements one
> or more §3.9 entities *against the signature in §3.9* — it does **not** depend on
> another milestone being implemented first, only on the contract, which already
> exists. Therefore milestones are **order-independent** and may be worked in
> parallel by concurrent agents; nothing is a blocker. If implementation surfaces a
> real ordering blocker, treat it as a **contract defect**: HALT, amend §3.9 and
> every citing checklist row + affected diagram, then resume. Do **not** introduce
> ad-hoc sequencing or patch around it locally. Where §3.1–§3.8 prose and §3.9
> disagree, **§3.9 wins** (the prose is illustrative; the registry is normative).

### 3.1 `capture/` — run on the current box
- `capture_packages(host=None) -> Packages` — `apt-mark showmanual` →
  `packages.apt`; `snap list` → `snaps`; `flatpak list --app --columns=…` →
  `flatpaks`. Records the **source** (release, ppas, remotes) so restore can
  re-add them before install.
- `capture_tree(paths, store, rules) -> list[BlobRef]` — walk `.bashrc`, `~/.config`,
  `/opt`, app config paths; each file → **content-addressed blob** (sha256) in the
  `BlobStore` under `payload/<profile>/blobs/`, deduped across profiles. Large blobs
  (`size > rules.big_bytes`) tagged `big` for optional exclusion per profile.
- `capture_app(host, app) -> AppCapture` — delegates to the app's adapter
  `capture()` (e.g. ollama: systemd override, `OLLAMA_MODELS`, shard dir).

### 3.2 `manifest.py` — the SSOT payload manifest (Pydantic)
```python
class Manifest(BaseModel):
    schema_version: str
    profile: str
    created_at_epoch_s: int            # passed in via args (no Date.now in workflows)
    source_host: str
    ubuntu_release: str                # e.g. "24.04"
    mode: Literal["repo", "live", "image"]
    target_disk: TargetDiskGuard       # by-id + model/serial/size
    filesystem: Literal["btrfs", "f2fs"]
    packages: Packages                 # apt + ppas, snaps, flatpaks + remotes
    apps: list[AppCapture]             # per-adapter captures
    blobs: list[BlobRef]               # sha256, size, path, tag
    identity: Identity                 # hostname, user, uid, realname, ssh keys
    adapter_order: list[str]           # install/apply order on first boot
```
> **Phase-2 seam:** `Manifest` + blobs are content-addressed and self-describing
> so a future `sync/` P2P module can replicate them between home machines and
> remote-booted USBs by hash range. The manifest carries `schema_version` and a
> `prev_manifest_sha` field forming an append-only chain for differential sync.

### 3.3 `guard.py` — disk-identity guard
- `TargetDiskGuard(by_id: str, model: str, serial: str, size_bytes: int)`.
- `list_candidate_disks()` — prints `/dev/disk/by-id/…` + `lsblk` model/serial/size
  so the operator can copy the id into a profile.
- Generated autoinstall `user-data` sets `interactive-sections: []` and an
  `early-commands` script that compares the live disk id to `target_disk.by_id`;
  **aborts install if mismatch** (no wrong-disk wipes). No encryption, no fsck
  pre-check, per spec.

### 3.4 `fs/` — layout builder
- `build_layout(manifest) -> AutoinstallStorage`:
  - **btrfs (default)**: single partition, subvols `@`, `@home`, `/boot` ext4.
  - **f2fs (option)**: root fs `format: f2fs` where Subiquity's storage schema
    permits; `/boot` ext4 for bootloader robustness; pre-flight warns on the few
    corners where f2fs root is rough.
- Emits the `storage.layout` section of autoinstall `user-data`.

### 3.5 `adapters/` — per-app restore modules (run inside cloud-init)
Contract each adapter implements:
```python
class Adapter(Protocol):
    name: str
    def capture(host) -> AppCapture: ...        # runs at capture time on source box
    def install(ctx) -> None: ...               # clean install from repo (first boot)
    def apply_config(ctx) -> None: ...          # re-apply config from payload, correct perms
    def verify(ctx) -> VerifyResult: ...        # post-check (e.g. `ollama list`)
```
- **`OllamaAdapter` (reference impl)** — `install`: official script/apt. `apply_config`:
  write `/etc/systemd/system/ollama.service.d/override.conf` from captured override,
  set `OLLAMA_MODELS`, `systemctl daemon-reload && systemctl enable --now ollama`,
  restore model shards into the configured dir as `ollama:ollama`. **Never copies
  stale binaries.**
- **`GenericAdapter`** — fallback: restore `~/.config/<app>` + captured config
  paths with original ownership/perms.

### 3.6 `picker/` — desktop-commander-style tree picker
- Textual app `PickerApp` over the proposed capture set; tick dirs/configs/apps
  into a profile. `gum`/`fzf` fallback when not a TTY. Emits/edits the profile's
  selection rules (an include/exclude glob set saved to `profiles/<name>/rules.toml`).

### 3.7 `build/` — the assembler (per mode × emit target)
- `extract_base_iso(iso_url) -> WorkDir` (`xorriso -osirrox`).
- `inject_seed(workdir, manifest)` — write `user-data` + `meta-data` nocloud seed
  under `/wowiso/seed/`, add kernel cmdline
  `autoinstall ds=nocloud-net;s=/wowiso/seed/`.
- `inject_payload(workdir, profile)` — rsync `payload/<profile>/` under `/wowiso/`.
- `edit_boot_menu(workdir)` — `boot/grub/grub.cfg` + `isolinux/txt.cfg`:
  Install / Live / Rescue entries.
- `rebuild_squashfs(workdir)` — (LIVE mode) `mksquashfs` the captured root tree.
- `repack_iso(workdir, out, label)` — `xorriso -as mkisofs`, **hybrid**
  (`-isohybrid-mbr`, `-eltorito-alt-boot -e EFI/boot/…`, original **volume label
  preserved**) → drop-in for YUMI/Ventoy/iVentoy.
- `write_usb(iso, device, multiboot=bool)` — dd, or GRUB2 multiboot stick
  (GPT/ESP/BIOS_GRUB, F2FS-first) reused from wowusb.

### 3.8 `netboot/` — iPXE/HTTP + iVentoy
- `publish_http(workdir, docroot)` — splits out `vmlinuz` + `initrd` + squashfs/payload.
- `render_ipxe_menu(manifest) -> str` — netboot.xyz-style menu script.
- `netboot_iso(ipxe_url) -> iso` — tiny chainloading ISO.
- iVentoy needs nothing special (the standard ISO is already iVentoy-compatible).

### 3.9 Entity registry — the frozen contract surface

Every entity below is **normative**: its name, file, and signature are fixed.
`CHECKLIST.md` tasks cite these by name. Because the contract surface exists
independently of any implementation, milestones carry **no dependency ordering**
(see the §3 concurrency clause). File locators are target paths (greenfield);
once code lands, line numbers are recorded in the registry update. Path prefix
`src/wowiso/` unless noted.

**`version.py`**
```python
# Derived by scripts/update-version.sh into version.txt; this module only READS it.
def current() -> str          # "MAJOR.MINOR.BUILD", e.g. "1.1.74918" (read from version.txt)
def version_code() -> int     # MAJOR*100000 + MINOR (BUILD excluded — monotonic for stores)
```

**`manifest.py`** — SSOT payload manifest (Pydantic v2)
```python
MANIFEST_SCHEMA_VERSION: str = "1"
class BlobRef(BaseModel):
    sha256: str
    size_bytes: int
    store_path: str
    owner_uid: int
    owner_gid: int
    mode: str                 # octal string, e.g. "0644"
    tag: Literal["config","big","shard","binary"]
class TargetDiskGuard(BaseModel):
    by_id: str                # /dev/disk/by-id/...
    model: str
    serial: str
    size_bytes: int
class Snap(BaseModel):
    name: str; channel: str = "stable"; classic: bool = False
class Flatpak(BaseModel):
    ref: str                  # e.g. com.example.App/x86_64/stable
    remote: str
class Packages(BaseModel):
    apt: list[str]
    apt_sources: list[str]    # sources.list.d entries to re-add before install
    snaps: list[Snap]
    flatpaks: list[Flatpak]
    flatpak_remotes: list[str]
class Identity(BaseModel):
    hostname: str
    username: str
    uid: int
    realname: str
    ssh_pubkeys: list[str]
class AppCapture(BaseModel):
    adapter: str              # registry key, e.g. "ollama"
    data: dict               # adapter-specific capture payload
    config_blobs: list[BlobRef]
class Manifest(BaseModel):
    schema_version: str
    profile: str
    created_at_epoch_s: int   # supplied by caller; no implicit clock inside models
    source_host: str
    ubuntu_release: str       # e.g. "24.04"
    mode: Literal["repo","live","image"]
    target_disk: TargetDiskGuard
    filesystem: Literal["btrfs","f2fs"]
    packages: Packages
    apps: list[AppCapture]
    blobs: list[BlobRef]
    identity: Identity
    adapter_order: list[str]
    prev_manifest_sha: str | None = None   # Phase-2 sync chain
    @classmethod
    def load(cls, path: Path) -> "Manifest": ...
    def dump(self, path: Path) -> None: ...
    def chain_sha(self) -> str: ...        # sha256 over canonical JSON; feeds prev_manifest_sha
```

**`guard.py`** — disk-identity guard
```python
def list_candidate_disks() -> list[TargetDiskGuard]
def render_early_commands(guard: TargetDiskGuard) -> str   # bash; `exit 1` on by-id mismatch
```

**`capture/blobs.py`** — content-addressed, deduped blob store
```python
class BlobStore:
    def __init__(self, root: Path): ...           # root = .../payload/<profile>/blobs
    def put(self, path: Path, tag: str) -> BlobRef
    def get(self, sha256: str) -> Path
    def has(self, sha256: str) -> bool
    def verify(self, sha256: str) -> bool         # re-hash on disk; has()->False if corrupt
```

**`capture/packages.py`**, **`capture/tree.py`**, **`capture/__init__.py`**
```python
# Host = thin subprocess-target shim (None => local). Defined in capture/__init__.py.
Host = object | None
def capture_packages(host: Host = None) -> Packages
class Rules(BaseModel):                          # capture/tree.py
    includes: list[str]
    excludes: list[str]
    big_bytes: int = 256 * 1024 * 1024
def capture_tree(paths: list[Path], store: BlobStore, rules: Rules) -> list[BlobRef]
def capture_app(adapter: "Adapter", host: Host = None) -> AppCapture
```

**`adapters/base.py`** — Adapter contract + registry
```python
@dataclass
class RestoreContext:                            # passed to install/apply_config/verify at first boot
    manifest: Manifest
    payload_root: Path          # where the /wowiso/ payload is materialised
    store: BlobStore
class VerifyResult(BaseModel):
    ok: bool
    detail: str
class Adapter(Protocol):
    name: str
    def capture(self, host=None) -> AppCapture: ...
    def install(self, ctx: RestoreContext) -> None: ...
    def apply_config(self, ctx: RestoreContext) -> None: ...
    def verify(self, ctx: RestoreContext) -> VerifyResult: ...
ADAPTERS: dict[str, Adapter]                     # seeded with {"generic": GenericAdapter()}
def get(name: str) -> Adapter                    # unknown key => GenericAdapter fallback
```

**`adapters/ollama.py`**, **`adapters/generic.py`**, **`adapters/firstboot.py`**
```python
class OllamaAdapter:                             # Adapter; name = "ollama"
    # capture: `systemctl cat ollama` -> override.conf; OLLAMA_MODELS env; shard dir -> blobs(tag="shard")
    # install:  `curl -fsSL https://ollama.com/install.sh | sh` (or apt if configured)
    # apply_config: write override.conf, set OLLAMA_MODELS, restore shards as ollama:ollama, daemon-reload + enable --now
    # verify: `ollama list` contains expected models -> VerifyResult
class GenericAdapter:                            # Adapter; name = "generic"
    # capture: no-op (tree capture covers ~/.config/<app>); install: no-op;
    # apply_config: restore config_blobs with original uid/gid/mode; verify: paths exist
def render_firstboot_script(manifest: Manifest) -> str   # /wowiso/wowiso-restore, invoked by cloud-init
```

**`fs/layout.py`**
```python
def build_layout(manifest: Manifest) -> dict          # autoinstall storage layout JSON
def warn_f2fs(manifest: Manifest) -> list[str]        # pre-flight caveats when filesystem == "f2fs"
```

**`build/` package — the assembler** (one function per file ⇒ file-exclusive
parallel tasks; signatures are the contract, file split is the parallelism lever)
```python
# build/workdir.py
@dataclass
class WorkDir:
    root: Path
    label: str                 # original ISO volume label, preserved on repack
# build/extract.py
def extract_base_iso(iso_path: Path) -> WorkDir        # xorriso -osirrox; cached under cache/base/<sha256>/
# build/seed.py
def inject_seed(workdir: WorkDir, manifest: Manifest) -> None
# build/payload.py
def inject_payload(workdir: WorkDir, profile: str) -> None
# build/bootmenu.py
def edit_boot_menu(workdir: WorkDir, manifest: Manifest) -> None
# build/squashfs.py
def rebuild_squashfs(workdir: WorkDir, src_root: Path) -> None   # LIVE only
# build/repack.py
def repack_iso(workdir: WorkDir, out: Path, label: str | None = None) -> Path
# build/usb.py
def write_usb(iso: Path, device: Path, multiboot: bool = False) -> None
# build/pipeline.py  — pass-2 orchestrator (the ONLY build/ file that imports the steps)
def build_repo(manifest: Manifest, base_iso: Path, emit: str, *, device: Path | None = None, http_root: Path | None = None) -> Path
def build_live(manifest: Manifest, emit: str, *, device: Path | None = None, http_root: Path | None = None) -> Path
def build_image(manifest: Manifest, base_iso: Path, emit: str, *, device: Path | None = None, http_root: Path | None = None) -> Path
# build/__init__.py — re-exports WorkDir + the three orchestrators
```

**`netboot/` package** (one function per file)
```python
# netboot/publish.py
def publish_http(workdir: WorkDir, docroot: Path) -> None
# netboot/ipxe.py
def render_ipxe_menu(manifest: Manifest) -> str
# netboot/netboot_iso.py
def netboot_iso(ipxe_url: str) -> Path            # tiny chainloading ISO
# netboot/__init__.py — re-exports
```

**`verify.py`** — end-to-end boot verifier (a real product command, not a throwaway)
```python
def verify_iso(iso: Path, manifest: Manifest, scratch_disk_id: str) -> VerifyResult
# boots `iso` under QEMU with a scratch disk whose by-id == manifest.target_disk.by_id;
# asserts: autoinstall proceeds, reaches first boot, cloud-init log shows package
# install + each adapter verify() ok (`ollama list` shows restored models).
```

**`cli.py`** — typer app (entry point `wowiso = wowiso.cli:app`)
```python
app: typer.Typer
# commands:
#   version
#   capture   --profile <name> [--target-disk-id <by-id>]
#   pick      --profile <name>
#   build {repo|live|image}  --profile <name> --base <iso> --emit {iso|usb|netboot} [--device /dev/sdX] [--http-root DIR]
#   guard list-disks
#   netboot   --profile <name> --http-root DIR
#   verify    --iso <path> [--scratch-disk-id <by-id>]
```

**`picker/app.py`**, **`picker/fallback.py`**, **`picker/rules.py`**
```python
class PickerApp:                                  # Textual app; reads proposed capture set, writes rules.toml
    def run(self, profile: str) -> None: ...
def fallback_pick(profile: str) -> None           # gum/fzf path when not a TTY
def load_rules(profile: str) -> Rules             # rules.py; maps rules.toml <-> capture.tree.Rules
```

> **`gui/`** (Tauri2) is out-of-process: it shells to the `cli.py` commands above.
> Its contract with the core is the CLI's stdout / exit-codes, not a Python import,
> so GUI work is fully decoupled from Python-core work and runs in parallel with it.

## 4. Data flow

```
SOURCE BOX                              BUILD HOST (same box ok)              TARGET
─────────                               ───────────────────────────            ──────
capture/  ──►  payload/<profile>/  ──►  build/  ──►  dist/*.iso | USB | netboot  ──► boot
   ▲              + manifest.json          (autoinstall + cloud-init)              │
   │                                                                        first-boot:
picker/ (rules.toml)                                                          adapters install+apply
                                                                              guard checks disk-id
```

## 5. Emit-target matrix

| Mode \ Emit | ISO (YUMI/Ventoy/iVentoy/dd) | USB (direct/multiboot) | Netboot (iPXE/HTTP) |
|-------------|------------------------------|------------------------|---------------------|
| REPO        | ✅ primary                   | ✅                     | ✅                  |
| LIVE        | ✅ primary                   | ✅                     | ⚠ (live-over-NFS)   |
| IMAGE       | ✅ primary                   | ✅                     | ✅                  |

## 6. Versioning + build number (CLAUDE.md)

- Scheme `MAJOR.MINOR.BUILD` (BUILD = epoch-minutes % 100000), derived by
  `scripts/update-version.sh` into `version.txt`; `version.py::current()` reads
  it (never hand-set). MAJOR ≥ 1; `versionCode = MAJOR*100000 + MINOR`.
- Build flow: `update-version.sh stamp` → build → on success `update-version.sh`
  (bumps MINOR), so the tree never falsely attests the just-built version.
- Surfaced: GUI status bar (bottom-right), `File → About`, executable filename
  (`wowiso-v1.1.74918-linux-amd64.deb` / `.msi`). Helper: `version.py::current()`.

## 7. Reuse from WowUSB-DS9

GRUB2 dual-arch (i386-pc + x86_64-efi) multiboot; GPT/ESP(512 MB FAT32)/
BIOS_GRUB(1 MB) layout; F2FS-first filesystem auto-selection (F2FS→exFAT→NTFS→
BTRFS, FAT32 only when no file >4 GB); Python CLI + Tauri2 packaging skeleton.
See `NOTICE`.

## 8. Roadmap (phased)

- **Phase 1 (now):** REPO mode → ISO; ollama + generic adapters; disk guard;
  btrfs/f2fs layout; Stitch-designed GUI shell; capture/picker. End-to-end QEMU
  smoke test.
- **Phase 2:** LIVE mode remaster; IMAGE mode bare-metal; Netboot/iPXE + iVentoy
  publish; USB multiboot emit; **P2P `sync/` module** (manifest+payload replication
  between home machines and remote-booted USBs, content-addressed diff sync over
  the manifest chain).
- **Phase 3:** more adapters (docker, tailscale, …); mobile GUI; refresh scheduler.

## 9. Verification

See `CHECKLIST.md` acceptance criteria and the QEMU boot harness in `tests/`.
End-to-end gate: each emitted ISO boots in QEMU; REPO reaches first boot and
`cloud-init` log shows packages installed + adapter `verify()` green
(`ollama list` shows restored models).
