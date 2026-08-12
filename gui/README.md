# wowiso GUI (Tauri2)

The front end for wowiso. Per `DOCS/ARCHITECTURE/windows-store-wsl-bridge.md`,
**the Python core is Linux-native** (apt/xorriso/mksquashfs), so:

- **Linux build** — the GUI shells to a **local** `wowiso` CLI.
- **Windows build** — the GUI shells to `wsl.exe -d Ubuntu-24.04 -- wowiso …`,
  hosting the unchanged core inside WSL2. This is what makes a Microsoft Store
  build functional rather than a non-launching shell.

```
Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
```

## Develop

```bash
cd gui
npm install
cargo tauri dev          # launches the window; shells to `wowiso` on PATH
```

The status bar (bottom-right) shows `version.py::current()` by asking the core
(`wowiso version`) — on Windows that runs inside WSL.

## Build / package

```bash
cargo tauri build                      # host-native bundles
cargo tauri build --bundles msix       # Windows: MSIX (the Store vehicle)
cargo tauri build --bundles msi        # Windows: MSI (the winget vehicle)
cargo tauri build --bundles deb,appimage,rpm   # Linux
```

`bundle.targets` is `"all"` in `tauri.conf.json`; select specific bundles with
`--bundles` (the Tauri2 pattern — a per-bundle array isn't accepted by the config schema).

### MSIX identity + Store submission

- `bundle.targets` + `--bundles msix` produce the MSIX. The MSIX **publisher** comes
  from the signing certificate subject (local dev: self-signed; Store: Partner Center
  re-signs on ingestion).
- The Partner Center **Identity Name** + **Publisher** are applied when you reserve the
  product name — see `DOCS/SUBMISSION.md` for the full, ordered, human-gated runbook.
- The app is a **full-trust** packaged desktop app (`runFullTrust`): it shells to WSL
  and writes ISOs to removable media.

## Layout

```
gui/
  index.html  src/{main.ts,screens.ts,app.css}   # vanilla-TS front end
  src-tauri/
    Cargo.toml  tauri.conf.json  build.rs
    src/{main.rs,lib.rs,wsl.rs}                   # wsl.rs = the WslBridge sidecar
    capabilities/default.json                     # invoke + event permissions
    icons/                                        # generated via `cargo tauri icon`
```

The 8-theme CLAUDE.md palette + Stitch-designed screens (M7.1) layer on top of the
structural theme system here (Light/Dark/System-Auto + platform tokens: Fluent on
Windows, Adwaita on Linux, macOS stack on darwin).
