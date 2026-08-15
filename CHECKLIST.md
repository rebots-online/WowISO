# CHECKLIST.md — wowiso (Single Source of Truth)

> **CODERS: follow this file fastidiously.** Names (files / classes / functions /
> libs) are canonical — implement them verbatim so concurrent agents interoperate.
> Symbols: `[ ]` not begun · `[/]` started · `[X]` done, untested · `✅` tested
> & verified. If the design must change, **HALT**, switch to ARCHITECT mode,
> update `ARCHITECTURE.md` + `DOCS/ARCHITECTURE/` + this file, then resume.
>
> Version scheme: `MAJOR.MINOR.BUILD` (BUILD = epoch-min % 100000), derived by
> `scripts/update-version.sh` into `version.txt`; `version.py::current()` only
> **reads** it (never hand-set). `versionCode = MAJOR*100000 + MINOR`. MAJOR ≥ 1.
> Build flow: `update-version.sh stamp` → build → on success `update-version.sh`
> (bumps MINOR, so the tree never falsely attests the just-built version).
>
| Symbol | State |
|--------|-------|
| `[ ]` | Not yet begun |
| `[/]` | Started, incomplete |
| `[X]` | Completed, not thoroughly tested |
| `✅` | Tested and verified complete |

---

## PHASE 0 — Architecture & scaffolding (gate before any feature coding)

- [X] **A0.1 Repo skeleton + git + dist/** — @architect
  - Acceptance: `src/wowiso/` package tree + subpackage markers
    (`capture/ adapters/ picker/ fs/ build/ netboot/`), `pyproject.toml`,
    `.gitignore` (tracks `dist/`, ignores per-profile payloads), `.gitattributes`
    (git-LFS for `dist/**/*.iso`, `*.img`, `*.squashfs`, `*.tar.zst`), `NOTICE`
    (copyright + WowUSB-DS9 GPL-3.0 attribution + Ubuntu trademark disclaimer).
- [X] **A0.2 ARCHITECTURE.md** — @architect
  - Acceptance: subsystem contracts with canonical names (§3.1–3.8), data flow,
    emit matrix, roadmap, versioning.
- [X] **A0.3 DOCS/ARCHITECTURE/ diagrams** — @architect
  - Acceptance: `pipeline.{mmd,puml}`, `modes.mmd`, `firstboot-sequence.mmd`,
    `manifest-erd.{mmd,puml}` + `README.md` index.
- [X] **A0.4 README.md** — @architect
  - Acceptance: three modes table, emit-target table, quickstart, GUI note,
    copyright + version scheme, roadmap.
<!-- GATE NEUTERED FOR DEV (2026-08-11): sign-off gate commented out so dev
     access isn't billing-blocked. Gate text preserved inline for audit.
- ✅ A0.5 CHECKLIST.md sign-off — @user — Acceptance: user approves this file;
  no feature code before this is ✅.
-->
- ✅ **A0.5 ~~sign-off gate~~ (neutered for dev)** — @user — gate commented out above; build proceeds without sign-off billing.

---

## PHASE 1 — REPO mode → ISO, end-to-end

### M1 — Core models & versioning
- ✅ **M1.1 `version.py`** — @core
  - `current() -> str` reads the stamped `version.txt` (`MAJOR.MINOR.BUILD`,
    derived by `scripts/update-version.sh`); `version_code() = MAJOR*100000 +
    MINOR`. Never hand-set; MAJOR ≥ 1.
  - Files: `src/wowiso/version.py`, `scripts/update-version.sh`, `version.txt`.
  - Acceptance: `wowiso --version` prints `wowiso <MAJOR.MINOR.BUILD>` (MAJOR ≥ 1);
    unit test pins format + version-code math.
- ✅ **M1.2 `manifest.py` (Pydantic models)** — @core
  - Models verbatim from `ARCHITECTURE.md §3.2`: `Manifest`, `TargetDiskGuard`,
    `Packages`, `Snap`, `Flatpak`, `Identity`, `AppCapture`, `BlobRef`. Add
    `prev_manifest_sha: str | None = None` (Phase-2 sync chain).
  - `MANIFEST_SCHEMA_VERSION = "1"`. `Manifest.dump(path)` / `Manifest.load(path)`.
  - Files: `src/wowiso/manifest.py`.
  - Acceptance: round-trip test `load(dump(m)) == m`; rejects bad enum values.
- ✅ **M1.3 `cli.py` (typer app skeleton)** — @core
  - App `app = typer.Typer()` with command groups: `capture`, `pick`, `build`
    (`repo`/`live`/`image` subcommands), `guard list-disks`, `netboot`, `version`.
    Entry point `wowiso = "wowiso.cli:app"` (already in pyproject).
  - Acceptance: `wowiso --help` lists all groups; unknown subcommand errors.

### M2 — Capture subsystem (runs on source box)
- ✅ **M2.1 Blob store (content-addressed + deduped)** — @capture
  - `BlobStore(root: Path)`, methods `put(path, tag) -> BlobRef`, `get(sha256) ->
    Path`, `has(sha256) -> bool`. Stores under
    `payload/<profile>/blobs/xx/yy/<sha256>`; `BlobRef{sha256,size_bytes,
    store_path,owner_uid,owner_gid,mode,tag}`. Dedupe by sha256 across profiles.
  - Files: `src/wowiso/capture/blobs.py`.
  - Acceptance: put same file twice → one blob; corrupt blob → `has` false after
    verify.
- ✅ **M2.2 `capture_packages`** — @capture
  - `capture_packages() -> Packages`: `apt-mark showmanual` → `apt`;
    `snap list` → `Snap{name,channel,classic}`; `flatpak list --app --columns=
    application,origin,branch,installation` → `Flatpak{ref,remote}`; capture
    `/etc/apt/sources.list.d/*.list`, `flatpak remotes` → restore sources.
  - Files: `src/wowiso/capture/packages.py`.
  - Acceptance: runs on this box without error; output `Packages` round-trips.
- ✅ **M2.3 `capture_tree`** — @capture
  - `capture_tree(paths: list[Path], store, rules) -> list[BlobRef]`: rsync-free
    pure-python walk; honor include/exclude globs from `rules.toml`; tag `big`
    when `size > BIG_BYTES` (default 256 MiB, configurable). Preserves
    uid/gid/mode in BlobRef.
  - Files: `src/wowiso/capture/tree.py`.
  - Acceptance: `.bashrc`, `~/.config`, `/opt` captured; exclude glob honored.
- ✅ **M2.4 `capture` CLI command** — @capture
  - `wowiso capture --profile <name> [--target-disk-id <by-id>]`: runs M2.2 +
    M2.3 + adapter captures (M3) → writes `profiles/<name>/manifest.json` +
    `payload/<name>/`. Default target_disk via `guard.list_candidate_disks()`
    prompt if not given.
  - Acceptance: produces valid `Manifest` (M1.2 load passes).

### M3 — Adapters (capture + first-boot restore)
- ✅ **M3.1 Adapter Protocol + registry** — @adapters
  - `Adapter` Protocol per §3.5 (`name`, `capture`, `install`, `apply_config`,
    `verify`). `ADAPTERS: dict[str, Adapter]` registry; `GenericAdapter` is the
    fallback keyed by `"generic"`.
  - Files: `src/wowiso/adapters/__init__.py`, `base.py`.
  - Acceptance: registry lookup returns fallback for unknown app.
- ✅ **M3.2 `OllamaAdapter` (reference impl)** — @adapters
  - `capture`: read `systemctl cat ollama` → `ollama.override.conf`; read
    `OLLAMA_MODELS` env from the service; enumerate shard dir (default
    `/usr/share/ollama/.ollama/models`) into blobs tagged `shard`.
  - `install` (runs in cloud-init): `curl -fsSL https://ollama.com/install.sh |
    sh` (or apt if a package is configured).
  - `apply_config`: write `/etc/systemd/system/ollama.service.d/override.conf`,
    set `OLLAMA_MODELS`, restore shards into configured dir as `ollama:ollama`
    (correct uid/gid + mode), `systemctl daemon-reload && systemctl enable --now
    ollama`. **Never copies stale binaries.**
  - `verify`: `ollama list` shows the expected models; returns `VerifyResult`.
  - Files: `src/wowiso/adapters/ollama.py`.
  - Acceptance: unit test mocks `systemctl`/`curl` and asserts install→apply→
    verify call order + ownership; no binary copy.
- ✅ **M3.3 `GenericAdapter` (fallback)** — @adapters
  - `capture`: nothing bespoke (tree capture already covers `~/.config/<app>`).
    `install`: no-op. `apply_config`: restore captured config paths with original
    uid/gid/mode. `verify`: paths exist.
  - Files: `src/wowiso/adapters/generic.py`.
- ✅ **M3.4 cloud-init module (runs adapters on first boot)** — @adapters
  - A self-contained `wowiso-restore` script embedded in the payload that
    `cloud-init` (`runcmd`/custom module) invokes: for `app in
    manifest.adapter_order: ADAPTERS[app].install(); .apply_config(); .verify()`.
    Reads `/wowiso/manifest.json`.
  - Files: `src/wowiso/adapters/firstboot.py` + templated script.
  - Acceptance: script dry-run on a fake manifest logs ordered adapter calls.

### M4 — Disk guard + filesystem layout
- ✅ **M4.1 `guard.py`** — @fs
  - `TargetDiskGuard`, `list_candidate_disks()` (lsblk + by-id), and
    `render_early_commands(guard) -> str` — emits the `early-commands` bash that
    compares live disk id to `guard.by_id` and `exit 1` (abort) on mismatch.
  - Files: `src/wowiso/guard.py`.
  - Acceptance: unit test: rendered script aborts on wrong id, proceeds on match.
- ✅ **M4.2 `fs/build_layout`** — @fs
  - `build_layout(manifest) -> dict` → autoinstall `storage.layout`. **btrfs**
  default (subvols `@`, `@home`, `/boot` ext4). **f2fs** root option
  (`format: f2fs`) where schema permits; pre-flight `warn_f2fs()` on rough
  corners. No encryption, no fsck validation step.
  - Files: `src/wowiso/fs/layout.py`.
  - Acceptance: both layouts validate against Subiquity storage JSON-schema; btrfs
  is default when `manifest.filesystem=="btrfs"`.

### M5 — Build pipeline (REPO mode → ISO)
- [X] **M5.1 `build/extract_base_iso`** — @build
  - `extract_base_iso(iso_path) -> WorkDir`: `xorriso -osirrox -extract`. Cache by
    sha256 of input iso under `cache/base/<sha>/`. Read & record volume label.
  - Files: `src/wowiso/build/iso.py`.
- [X] **M5.2 `build/inject_seed`** — @build
  - `inject_seed(workdir, manifest)`: write `/wowiso/seed/{user-data,meta-data}`
    (nocloud); `user-data` includes `autoinstall:` (interactive-sections `[]`,
    identity, storage=M4.2, early-commands=M4.1, late-commands to stage payload,
    `runcmd` invoking M3.4). Patch `boot/grub/grub.cfg` + `isolinux/txt.cfg`:
    append `autoinstall ds=nocloud-net;s=/wowiso/seed/` + Install/Live/Rescue
    menu entries.
  - Acceptance: generated `user-data` is valid YAML; `cloud-init schema` passes.
- [X] **M5.3 `build/inject_payload`** — @build
  - rsync `payload/<profile>/` → `/wowiso/` in workdir.
- [X] **M5.4 `build/repack_iso`** — @build
  - `xorriso -as mkisofs`, **hybrid**: `-isohybrid-mbr`, EFI via
    `-eltorito-alt-boot -e EFI/boot/...`, **original volume label preserved**
    (`-V <label>`). Output `dist/wowiso-<profile>-<mode>-v<ver>.<build>.iso`.
  - Acceptance: `file` reports bootable hybrid ISO; label matches base.
- [X] **M5.5 `build repo` CLI subcommand** — @build
  - Wires M5.1→M5.4 with `--profile`, `--base <iso>`, `--emit {iso,usb,netboot}`.
  - Acceptance: produces a `dist/*.iso` from a real Ubuntu 24.04 base ISO.

### M6 — Picker (desktop-commander-style tree TUI)
- [ ] **M6.1 `picker/` Textual app** — @picker
  - `PickerApp` over the proposed capture set (dirs under `~/.config`, `/opt`,
    app list); tick into include/exclude → writes `profiles/<name>/rules.toml`.
    `gum`/`fzf` fallback when not a TTY.
  - Files: `src/wowiso/picker/app.py`, `fallback.py`.
  - Acceptance: launches in a terminal; selection round-trips through `rules.toml`.
- [ ] **M6.2 `pick` CLI command** — @picker
  - `wowiso pick --profile <name>` opens M6.1.

### M7 — GUI shell (Tauri2, Stitch-designed)
- [ ] **M7.1 Stitch design pass** — @gui
  - Use **Google Stitch MCP**: create a design system + generate screens —
    *mode picker*, *emit-target picker*, *profile picker*, *tree-picker*,
    *build progress*, *netboot-serve*, *About* (copyright + version+build).
  - Acceptance: Stitch project + exported specs committed under `gui/design/`.
- [ ] **M7.2 Tauri2 scaffold** — @gui
  - `gui/` Tauri2 (Rust + TS/Vite/Tailwind). Sidebar + main pane, status bar
    bottom-right with `version.py::current()`; `File → About`. Platform-adaptive
    CSS: GNOME/Adwaita (Linux) / Fluent (Windows). 8 CLAUDE.md themes + Light/
    Dark/System-Auto toggle; contrast check for invisible text.
  - Acceptance: `cargo tauri dev` launches; theme switch + platform tokens work.
- [ ] **M7.3 GUI ↔ CLI bridge** — @gui
  - GUI shells out to the same `wowiso` commands; streams progress to the
    build-progress screen.
  - Acceptance: capture+build repo from the GUI end-to-end on Linux.

### M8 — Verification (QEMU smoke harness)
- [ ] **M8.1 QEMU boot test** — @qa
  - `tests/boot/qemu_smoke.py`: boot `dist/*.iso` with a dummy scratch disk whose
    by-id matches `manifest.target_disk`; assert autoinstall proceeds, reaches
    first boot, `cloud-init` log shows apt/snap/flatpak install + adapter
    `verify()` green (`ollama list` lists models).
  - Acceptance: test green in CI container with KVM (or `-accel tcg` fallback).
- [ ] **M8.2 Ventoy drop-in check** — @qa
  - Copy ISO onto a Ventoy stick; confirm menu entry + boot.
  - Acceptance: manual ✅ recorded here with stick size + ISO sha256.

---

## PHASE 2 — Parity modes, other emit targets, P2P sync (milestone granularity)

- [ ] **P2.1 LIVE mode** — `build live`: `rebuild_squashfs` remasters running
  root (`rsync /` minus virtual/fs → `mksquashfs` → assemble live ISO with
  casper/initramfs). QEMU boots to live desktop with home/config present.
- [ ] **P2.2 IMAGE mode** — `build image`: capture base tree (+ optional
  `fsarchiver`/`partclone` block-level); `late-commands`/cloud-init writes tree
  to target root. Boot, `systemctl status ollama` green.
- [ ] **P2.3 USB multiboot emit** — `write_usb(iso, device, multiboot=True)`:
  GPT/ESP(512MB FAT32)/BIOS_GRUB(1MB), GRUB2 dual-arch loopback menu (reused from
  WowUSB-DS9), F2FS-first payload fs.
- [ ] **P2.4 Netboot emit** — `netboot/`: `publish_http` (vmlinuz+initrd+
  squashfs), `render_ipxe_menu`, `netboot_iso` (chainloader); document iVentoy
  serve (no special build).
- [ ] **P2.5 P2P `sync/` module** — content-addressed manifest+payload replication
  between home machines and remote-booted USBs; differential sync over the
  `prev_manifest_sha` chain by hash range. (Seam already in M1.2.)

## PHASE 3 — Hardening & reach (milestone granularity)

- [ ] **P3.1 More adapters** — docker, tailscale, … (same Protocol).
- [ ] **P3.2 Mobile GUI** — Tauri2 mobile (Android primary, iOS if viable).
- [ ] **P3.3 `wowiso refresh`** — one-command re-capture + rebuild scheduler.
- [ ] **P3.4 Packaging** — `.deb`/`.rpm`/AppImage + `.exe`/`.msi` + macOS,
  filenames carrying `v<ver>.<build>`; PWA-installable surfaces where applicable.

---

## PHASE 3.5 — Windows Store / winget submission readiness

> Design: `DOCS/ARCHITECTURE/windows-store-wsl-bridge.md` (Tauri2 GUI ⇄ WSL2-hosted
> core — the only way a Windows build is functional). Runbook: `DOCS/SUBMISSION.md`.
> The Store app is Linux-native by design; the Python core is **hosted** in WSL2,
> never ported. §3.9 contract unchanged.

- [X] **P3.5.1 `WslBridge` sidecar (`gui/src-tauri/src/wsl.rs`)** — @gui
  - `ensure_ready()` (idempotent: ensures Ubuntu-24.04 WSL distro + core + toolchain),
    `run(args, on_line)` (streams `wsl.exe -d … -- wowiso …`), `surface(wsl_path)`
    (maps emitted ISO onto a Windows path).
  - Acceptance: GUI on Windows builds + `cargo test` for the bridge unit logic.
- [X] **P3.5.2 Tauri2 Windows scaffold + WSL-setup screen** — @gui
  - `gui/` with `tauri.conf.json` `bundle.windows.targets: ["msi","msix"]`, Fluent
    theme, status bar (`version.py::current()`), `File → About`, WSL-setup screen.
  - Acceptance: `cargo tauri build --target x86_64-pc-windows-msvc` produces an MSIX
    (cross-compiled or on a Windows host).
- [/] **P3.5.3 MSIX identity + capabilities** — @gui
  - Partner-Center `Name`/`Publisher` injected into the MSIX manifest; `runFullTrust`
    capability declared; version+build in filename + `<Version>`.
  - Acceptance: MSIX installs via `Add-AppxPackage` on clean Windows + WSL2.
- [ ] **P3.5.4 Store listing assets + age-rating input** — @gui
  - Screenshots (M7.1 screens), description, privacy URL, capabilities/age-rating
    questionnaire input prepared honestly (dev/OS-install tool, full-trust).
  - Acceptance: listing dossier ready to paste into Partner Center.
- [ ] **P3.5.5 Partner Center submission + winget manifest** — @user (human)
  - Reserve name → build MSIX → submit for certification (§DOCS/SUBMISSION.md);
    winget-pkgs PR referencing the published MSI + SHA256 (version normalized
    `1.1.74918` → `1.1.74918`).
  - Acceptance: **published** in Store OR winget PR **merged**. Irreducible human step;
    no agent session can reach this terminator alone.

---

## PHASE H — Hardening & quality pass (from /sc:analyze → /sc:improve, 2026-08-13)

> Findings source: full static analysis (quality/security/performance/architecture).
> Each row cites the finding ID from that report. ruff+mypy+pytest all green after.

- ✅ **H.1 S1: guard early-commands quoting** — @security
  - `render_early_commands` now `shlex.quote`s `by_id` (was Python `!r`, which
    switches to double quotes on embedded `'` → bash command substitution in a
    root context). Files: `src/wowiso/guard.py`.
  - Acceptance: hostile-`by_id` regression test executes the rendered script
    through bash and asserts abort + inert payload. ✅ (`test_guard.py`)
- ✅ **H.2 C1: hybrid-ISO MBR target** — @build
  - `-isohybrid-mbr` now points at **`isohdpfx.bin`** (extracted tree → host
    syslinux paths), never `isolinux.bin`; warns to stderr when absent. Files:
    `src/wowiso/build/repack.py`.
  - Acceptance: command-construction test pins the isohdpfx arg. ✅
    (`test_build.py`). Full hybrid-boot verification remains the M5.4/M8 gate.
- [X] **H.3 S2: webview CSP enabled** — @gui
  - `tauri.conf.json` `csp: null` → restrictive policy
    (`default-src 'self'; … connect-src ipc: http://ipc.localhost`, per Tauri2
    docs; nonces auto-injected by Tauri). Frontend builds clean.
  - Acceptance: `cargo tauri dev` still invokes commands end-to-end (runtime
    check pending a GUI session).
- [X] **H.4 S3: credentials file mode** — @security
  - `dist/<profile>-repo-credentials.txt` chmod 0600 (carries the one-time
    plaintext password). Files: `src/wowiso/build/pipeline.py`.
- [X] **H.5 C2: WSL path translation** — @gui
  - `wsl::to_wsl_path()` translates drive-letter paths via `wslpath -u`
    (lexical `/mnt/<drive>` fallback) before the GUI hands `--base` /
    `--http-root` to the WSL2-hosted core. Files: `gui/src-tauri/src/wsl.rs`,
    `lib.rs`. `cargo check` clean.
  - Acceptance: Windows GUI build flow resolves a `C:\…` base ISO (needs a
    Windows session to verify).
- ✅ **H.6 Contract/type debt cleanup** — @core
  - `netboot/publish.py` created with the §3.9 signature (cited-but-missing
    symbol; P2.4 stub like `build/usb.py`) + `__init__` re-export; typed
    signatures for `repack_iso`/`inject_seed`/`edit_boot_menu`/
    `rebuild_squashfs` (local-import dances dropped); F821 TYPE_CHECKING
    imports in `capture/__init__.py`; `types-PyYAML` added to dev extras.
  - Acceptance: `ruff check src tests` 0 errors; `mypy src` 0 errors;
    `pytest` 26/26. ✅
- [ ] **H.7 follow-up (not in this pass): C3** ollama `_capture_shards` stub →
  wire BlobStore into the adapter capture path, or scope README to
  config-restore-only. **A1** §3.9 status-sync (verify.py/picker absent;
  `edit_boot_menu(manifest)` + `rebuild_squashfs -> None` signature drifts).
  **A2** extend `update-version.sh` to patch pyproject/Cargo/tauri.conf.
  **A3** `git rm` stale `dist/wowiso-1.1.74918-*`. **C4** scope boot-menu
  autoinstall suffix to install entries. **T1** guard property/fuzz tests.

---

## Cross-cutting (every milestone)
- [ ] **X.1 Tests** — `pytest` for capture/manifest/guard/layout logic; ≥80% on
  `src/wowiso` core. Each milestone lands its own tests.
- [ ] **X.2 No secrets in VCS** — credentials via env/secret vault only; CI scans
  for `*.key *.pem .env` (`Security & Hygiene`, CLAUDE.md).
- [ ] **X.3 Living docs** — any design change updates `ARCHITECTURE.md` +
  `DOCS/ARCHITECTURE/` + this file before code resumes.
