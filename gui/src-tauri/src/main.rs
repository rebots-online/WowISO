// Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
// Prevents an additional console window on Windows in release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    wowiso_gui_lib::run()
}
