// Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
//! WslBridge — the transport that makes a Windows build functional.
//!
//! The wowiso Python core is Linux-native (apt/xorriso/mksquashfs).
//! On Windows the GUI does **not** port it; it hosts the unchanged `wowiso`
//! CLI inside a WSL2 Ubuntu-24.04 distro and shells to it via `wsl.exe`. On
//! Linux the GUI calls `wowiso` directly. See
//! `DOCS/ARCHITECTURE/windows-store-wsl-bridge.md`.

use std::process::Command;

pub const WSL_DISTRO: &str = "Ubuntu-24.04";

/// Build a `wowiso` invocation appropriate to the platform.
///
/// - Windows: `wsl.exe -d Ubuntu-24.04 -- wowiso <args…>`
/// - other:   `wowiso <args…>` (core runs locally)
pub fn build_command(args: &[String]) -> Command {
    #[cfg(target_os = "windows")]
    {
        let mut c = Command::new("wsl.exe");
        c.args(["-d", WSL_DISTRO, "--", "wowiso"]);
        c.args(args);
        c
    }
    #[cfg(not(target_os = "windows"))]
    {
        let mut c = Command::new("wowiso");
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
