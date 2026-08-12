# Windows Store / winget — WSL2 bridge architecture

> Companion to `ARCHITECTURE.md`. Answers the question: *how can a Linux-native
> Ubuntu ISO builder ship as a functional Microsoft Store app on Windows?*
> This is a **design** artifact (DESIGN phase). It defines a Phase-3.5 surface
> that **does not exist yet**; nothing here is implemented.

```
Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
```

## 1. Why a bridge is required (not optional)

`ARCHITECTURE.md §3` shells, in every subsystem, to **Linux-only** primitives:

| Subsystem | Primitives | Exist on bare Windows? |
|-----------|------------|------------------------|
| `capture/` | `apt-mark`, `snap list`, `flatpak list`, `systemctl cat` | ❌ |
| `build/` | `xorriso`, `mksquashfs`, `rsync`, `grub-mkimage` | ❌ |
| `guard.py` | `/dev/disk/by-id/*`, `lsblk` | ❌ |
| `fs/layout.py` | Subiquity `autoinstall` (consumed by the Ubuntu installer) | ❌ |
| `adapters/` | `systemctl`, `/etc/systemd/system/` | ❌ |

A Tauri2 Windows binary that imported or shelled to these directly would **launch
and then fail at the first `apt-mark` call**. Packaging such a binary into an
MSIX and submitting it to the Store would produce a non-functional listing —
cargo-cult packaging, explicitly rejected by the purposive reading of the
CLAUDE.md cross-platform mandate (INC-12: reason to purpose, not to the
co-clause).

The only way a Windows install of wowiso can do its job is to run the
Python core **inside a Linux environment hosted by Windows**. The supported,
Store-acceptable way to do that is **WSL2**.

## 2. The bridge (one sentence)

> The Tauri2 GUI is a native Windows (Fluent-themed) front end that invokes the
> **unchanged** `wowiso` CLI **inside a WSL2 Ubuntu-24.04 distro** via
> `wsl.exe`, streaming its stdout/stderr to the build-progress screen and
> surfacing emitted ISOs onto a Windows-accessible path.

The Python core is **not ported**; it is **hosted**. This preserves the §3.9
frozen contract verbatim — the bridge is a transport layer, not a fork.

## 3. Component map

```
Windows host
┌──────────────────────────────────────────────────────────────┐
│  wowiso GUI  (Tauri2, Fluent theme, MSIX-packaged) │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  screens: mode/emit/profile pickers · tree-picker ·    │  │
│  │  build-progress (stdout stream) · WSL-setup · About    │  │
│  └────────────────────────────────────────────────────────┘  │
│         │ WslBridge (sidecar)                                │
│         │   wsl.exe -d Ubuntu-24.04 -- wowiso <cmd> ...   │
└─────────┼────────────────────────────────────────────────────┘
          │
   ═══════╪═════════════════ WSL2 boundary (hvsocket/9p) ═══════
          │
┌─────────▼────────────────────────────────────────────────────┐
│  WSL2: Ubuntu-24.04 distro  (the "source box" / "build host")│
│  ┌────────────────────────────────────────────────────────┐  │
│  │  wowiso core (pipx install)                  │  │
│  │  + apt deps: xorriso squashfs-tools rsync grub-pc-bin  │  │
│  │  + (capture source) apt/snap/flatpak/systemctl         │  │
│  └────────────────────────────────────────────────────────┘  │
│  payload/<profile>/ + manifest.json  ──►  dist/*.iso         │
└─────────┬────────────────────────────────────────────────────┘
          │ emit surface: /mnt/c/Users/.../wowiso/dist
          ▼
   Windows filesystem  ──►  Rufus / Ventoy / dd
```

## 4. The `WslBridge` contract (GUI side)

> Lives in `gui/src-tauri/src/wsl.rs`. **Not** a §3.9 entity (the GUI is
> out-of-process by design, §3.9 closing note); this is its Windows-only
> transport contract.

```rust
struct WslBridge { distro: DistroSpec }

impl WslBridge {
    /// Ensure the managed Ubuntu-24.04 distro exists and the core is installed
    /// (idempotent). Runs on first launch + from the WSL-setup screen.
    fn ensure_ready(&self) -> Result<Ready, WslError>;

    /// Stream a `wowiso` command; line-buffered stdout/stderr → GUI.
    /// Exit code is the contract (unchanged from cli.py).
    fn run(&self, args: &[&str], on_line: impl FnMut(&str)) -> ExitCode;

    /// Map an emitted ISO onto a Windows path (\\wsl$\ or /mnt/c surface).
    fn surface(&self, wsl_path: &Path) -> PathBuf;
}
```

`Host` capture (§3.9 `capture/__init__.py::Host`) already anticipates a non-local
target: `capture_packages(host=...)`. On Windows, `host` defaults to the managed
WSL distro; for capturing a *different* real Linux box, the same shim targets an
SSH host. **No core change is required** — the bridge selects the host.

## 5. Distros: bundle vs. require

| Strategy | Store UX | Package size | Verdict |
|----------|----------|--------------|---------|
| **Require** user's existing Ubuntu-24.04 WSL | light install; dependency on user setup | small MSIX | MVP / first submission |
| **Bundle** a custom `.wsl` image with core + toolchain preinstalled | one-click | +300–600 MB | v2 / "works out of the box" |

First Store submission uses **require** (smaller, faster certification); the
WSL-setup screen walks the operator through `wsl --install -d Ubuntu-24.04` and
then bootstraps `xorriso squashfs-tools rsync grub-pc-bin` + `pipx install
wowiso` inside it. The MSIX declares `wsl` as a dependency.

## 6. Packaging + identity

- **Tauri2 bundle targets (Windows):** `["msi", "msix"]`. MSIX is the Store
  vehicle; MSI is the winget/download vehicle.
- **Full-trust packaged app:** the GUI shells to `wsl.exe` and writes ISOs to
  removable media → it is a **Desktop Bridge / `runFullTrust`** app, not a
  sandboxed UWP. Declared in the MSIX manifest.
- **Identity** comes from Partner Center (reserve name → `Name` + `Publisher`).
  No code is signed with a real identity until that reservation exists; local
  dev uses a self-signed cert.
- **Version+build:** filename + MSIX `<Version>` carry `version.py::current()`
  per CLAUDE.md (e.g. `wowiso_1.1.74918_x64.msix`).

## 7. What this does NOT change

- §3.9 frozen contract: **unchanged**. The bridge is transport, not a fork.
- Linux build (`.deb`/`.rpm`/AppImage): the GUI there shells to a **local**
  `wowiso` directly (no WSL). The `WslBridge` is compiled in only for the
  `windows` target (`#[cfg(windows)]`).
- The Store app's job is the same job: capture → build → emit. Only the host of
  the Python core moves.

## 8. Open design questions (resolve before Phase 3.5 implementation)

1. **Capture target semantics on Windows.** "Capture *this* box" on Windows
   means capture *the WSL distro*, not the Windows host. Is that the intended
   product behavior, or is the Windows app primarily a **build/emit** front end
   for profiles captured elsewhere (e.g. on a real Linux box over SSH)? — *This
   is the key product question; it shapes the whole Windows UX.*
2. **ISO→USB on Windows.** Writing a hybrid ISO to a stick on Windows should use
   the OS-native path (Rufus/Ventoy, or a UDF/USB helper), not `dd` inside WSL.
   Decide whether the GUI shells to Rufus or ships a small USB writer.
3. **Distro lifecycle.** Who owns WSL distro teardown/uninstall? Bundle strategy
   (§5) changes the answer.

These are flagged here, not solved, per DESIGN phase.
