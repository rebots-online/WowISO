// Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
//! wowiso GUI backend (Tauri2). Shells to the `wowiso` CLI —
//! locally on Linux, inside WSL2 on Windows — and streams progress to the
//! frontend via `progress` events.

mod wsl;

use std::io::BufRead;
use std::path::PathBuf;
use std::process::Stdio;

use tauri::Emitter;

/// The bundled Python core (`core-dist/`, shipped as a Tauri resource), when
/// present. Resolved via the resource dir so it works identically in the deb,
/// rpm, and AppImage layouts; `None` in dev (falls back to `wowiso` on PATH).
fn bundled_core_dir(app: &tauri::AppHandle) -> Option<PathBuf> {
    use tauri::Manager;
    let core = app.path().resource_dir().ok()?.join("core-dist");
    core.join("bin").join("wowiso").is_file().then_some(core)
}

/// Stream a `wowiso` command's combined output as `progress` events.
/// Returns the process exit code.
fn run_streaming(app: tauri::AppHandle, args: Vec<String>) -> Result<i32, String> {
    let core = bundled_core_dir(&app);
    let mut cmd = wsl::build_command(&args, core.as_deref());
    cmd.stdout(Stdio::piped()).stderr(Stdio::piped());
    let mut child = cmd.spawn().map_err(|e| format!("spawn wowiso: {e}"))?;

    let stdout = child.stdout.take().ok_or("no stdout")?;
    let stderr = child.stderr.take().ok_or("no stderr")?;

    // pump stderr on its own thread so order is non-blocking
    let app_err = app.clone();
    std::thread::spawn(move || {
        let reader = std::io::BufReader::new(stderr);
        for line in reader.lines().flatten() {
            let _ = app_err.emit("progress", format!("[stderr] {line}"));
        }
    });

    let reader = std::io::BufReader::new(stdout);
    for line in reader.lines().flatten() {
        let _ = app.emit("progress", line);
    }

    let status = child.wait().map_err(|e| format!("wait: {e}"))?;
    Ok(status.code().unwrap_or(-1))
}

#[tauri::command]
fn get_version(app: tauri::AppHandle) -> String {
    // Honors version.py::current() by asking the core itself (bundled if present).
    let out = wsl::build_command(&["version".into()], bundled_core_dir(&app).as_deref())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .output();
    match out {
        Ok(o) if o.status.success() => {
            String::from_utf8_lossy(&o.stdout)
                .lines()
                .next()
                .unwrap_or("wowiso (core version unavailable)")
                .to_string()
        }
        _ => "wowiso (core not on PATH)".into(),
    }
}

#[tauri::command]
fn wsl_ensure_ready() -> Result<String, String> {
    if !wsl::required() {
        return Ok(
            "WSL not required on this platform; the Python core runs locally.".into(),
        );
    }
    // Windows path: ensure the managed distro + core + toolchain exist.
    #[cfg(target_os = "windows")]
    {
        use std::process::Stdio;
        // Is the distro installed?
        let listed = wsl::wsl_raw(&["-l", "-q"])
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .output()
            .map_err(|e| format!("wsl -l: {e}"))?;
        let names = String::from_utf16_lossy(
            &String::from_utf8_lossy(&listed.stdout)
                .encode_utf16()
                .collect::<Vec<u16>>(),
        );
        if !names.contains(wsl::WSL_DISTRO) {
            // Bootstrap: install the distro (requires reboot on first-ever WSL use;
            // surfaced honestly to the operator rather than silently failing).
            return Err(format!(
                "{} WSL distro not found. Run `wsl --install -d {}`, reboot if prompted, \
                 then retry. (Bundle-the-distro strategy is P3.5 v2.)",
                wsl::WSL_DISTRO, wsl::WSL_DISTRO
            ));
        }
        // Is the core installed inside the distro?
        let probe = wsl::build_command(&["--version".into()], None)
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .output();
        let core_ok = matches!(probe, Ok(o) if o.status.success());
        if !core_ok {
            // Bootstrap the core + toolchain inside the distro.
            let bootstrap = wsl::wsl_raw(&[
                "-d", wsl::WSL_DISTRO, "--", "bash", "-lc",
                "sudo apt-get update && \
                 sudo apt-get install -y xorriso squashfs-tools rsync grub-pc-bin pipx && \
                 pipx install wowiso || true",
            ])
            .status()
            .map_err(|e| format!("bootstrap: {e}"))?;
            if !bootstrap.success() {
                return Err("core bootstrap inside WSL failed; see WSL setup logs".into());
            }
        }
        return Ok(format!("{} ready; wowiso core installed.", wsl::WSL_DISTRO));
    }
    #[cfg(not(target_os = "windows"))]
    {
        Ok("no-op (non-Windows)".into())
    }
}

#[tauri::command]
fn start_capture(app: tauri::AppHandle, profile: String) -> Result<i32, String> {
    run_streaming(app, vec!["capture".into(), "--profile".into(), profile])
}

#[tauri::command]
fn start_pick(app: tauri::AppHandle, profile: Option<String>) -> Result<i32, String> {
    // NOTE: the picker is a real TUI; in the GUI it streams best-effort. The
    // external-terminal experience is the M6 polish target.
    let p = profile.unwrap_or_else(|| "default".into());
    run_streaming(app, vec!["pick".into(), "--profile".into(), p])
}

#[tauri::command]
fn start_build(
    app: tauri::AppHandle,
    profile: String,
    base: String,
    mode: String,
    emit: String,
) -> Result<i32, String> {
    run_streaming(
        app,
        vec![
            "build".into(), mode, "--profile".into(), profile,
            // the core may run inside WSL2 — hand it a path it can resolve (C2)
            "--base".into(), wsl::to_wsl_path(&base), "--emit".into(), emit,
        ],
    )
}

#[tauri::command]
fn start_netboot(app: tauri::AppHandle, profile: String, http_root: String) -> Result<i32, String> {
    run_streaming(
        app,
        vec![
            "netboot".into(), "--profile".into(), profile,
            "--http-root".into(), wsl::to_wsl_path(&http_root),
        ],
    )
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_version,
            wsl_ensure_ready,
            start_capture,
            start_pick,
            start_build,
            start_netboot,
        ])
        .run(tauri::generate_context!())
        .expect("error while running wowiso GUI");
}
