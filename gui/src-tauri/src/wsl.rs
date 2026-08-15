// Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
//! WslBridge — the transport that makes a Windows build functional.
//!
//! The wowiso Python core is Linux-native (apt/xorriso/mksquashfs).
//! On Windows the GUI does **not** port it; it hosts the unchanged `wowiso`
//! CLI inside a WSL2 Ubuntu-24.04 distro and shells to it via `wsl.exe`. On
//! Linux the GUI calls `wowiso` directly. See
//! `DOCS/ARCHITECTURE/windows-store-wsl-bridge.md`.

use std::process::Command;

#[cfg_attr(not(target_os = "windows"), allow(dead_code))] // used only in windows-gated paths
pub const WSL_DISTRO: &str = "Ubuntu-24.04";

/// Build a `wowiso` invocation appropriate to the platform.
///
/// - Windows: `wsl.exe -d Ubuntu-24.04 -- wowiso <args…>`
/// - other:   the bundled core (`core-dist/bin/wowiso`, a Tauri resource) when
///            present, else `wowiso` from PATH (dev fallback)
pub fn build_command(args: &[String], core_dir: Option<&std::path::Path>) -> Command {
    #[cfg(target_os = "windows")]
    {
        let _ = core_dir; // the Linux core bundle is not used on Windows
        let mut c = Command::new("wsl.exe");
        c.args(["-d", WSL_DISTRO, "--", "wowiso"]);
        c.args(args);
        c
    }
    #[cfg(not(target_os = "windows"))]
    {
        let mut c = match core_dir.map(|d| d.join("bin").join("wowiso")) {
            Some(p) if p.is_file() => Command::new(p),
            _ => Command::new("wowiso"),
        };
        c.args(args);
        c
    }
}

/// (Windows only) raw `wsl.exe` invocation for distro management.
#[cfg(target_os = "windows")]
pub fn wsl_raw(args: &[&str]) -> Command {
    let mut c = Command::new("wsl.exe");
    c.args(args);
    c
}

/// Whether the WSL2 bridge is required (true only on Windows).
pub fn required() -> bool {
    cfg!(target_os = "windows")
}

/// Translate a Windows filesystem path to its WSL (Linux) equivalent.
///
/// The GUI hands us host paths (typed `C:\…` values, file pickers); the core
/// running inside WSL2 only understands `/mnt/c/…`. Drive-letter paths are
/// converted via the distro's own `wslpath -u` (honors a custom automount
/// root); if that fails we fall back to the standard `/mnt/<drive>/…` lexical
/// mapping. Anything that is not a Windows path is returned unchanged.
pub fn to_wsl_path(path: &str) -> String {
    #[cfg(not(target_os = "windows"))]
    {
        path.to_string()
    }
    #[cfg(target_os = "windows")]
    {
        let p = path.trim();
        let b = p.as_bytes();
        let looks_like_win = b.len() >= 3
            && b[0].is_ascii_alphabetic()
            && b[1] == b':'
            && (b[2] == b'\\' || b[2] == b'/');
        if !looks_like_win {
            return p.to_string();
        }
        // Prefer the distro's own mapping (handles non-/mnt automount roots).
        // Relayed Linux stdout arrives as plain UTF-8 — unlike `wsl -l` output,
        // which is UTF-16 and needs the decode dance in lib.rs.
        if let Ok(out) = wsl_raw(&["-d", WSL_DISTRO, "--", "wslpath", "-u", p]).output() {
            if out.status.success() {
                let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
                if !s.is_empty() {
                    return s;
                }
            }
        }
        // Lexical fallback: `C:\x\y` | `C:/x/y` -> `/mnt/c/x/y`.
        // The `C:\` prefix is ASCII, so byte 3 is always a char boundary.
        let drive = (b[0] as char).to_ascii_lowercase();
        let rest = p[3..].replace('\\', "/");
        format!("/mnt/{drive}/{rest}")
    }
}
