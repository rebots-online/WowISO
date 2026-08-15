#!/usr/bin/env bash
# =============================================================================
# scripts/bundle-core.sh — bundle the wowiso Python core as a Tauri resource.
#
# Produces gui/src-tauri/core-dist/{site-packages,bin/wowiso,version.txt},
# pinned to the Ubuntu 24.04 SYSTEM interpreter (/usr/bin/python3 = 3.12) so the
# bundled wheels (pydantic_core .so etc.) match target machines — never the dev
# venv (conda 3.10) or $PATH python3 (linuxbrew 3.14), whose tags would not
# import on a clean Ubuntu box. Run before `cargo tauri build`; the Rust side
# resolves the bundle via tauri::Manager::resource_dir() (falls back to PATH
# `wowiso` in dev). Keeps the Linux artifacts self-contained: no pipx install.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

PY=/usr/bin/python3
DEST=gui/src-tauri/core-dist

[ -x "$PY" ] || { echo "bundle-core: $PY missing (Ubuntu 24.04 baseline required)" >&2; exit 1; }
command -v uv >/dev/null || { echo "bundle-core: uv required (uv pip install --target)" >&2; exit 1; }

rm -rf "$DEST"
uv pip install --python "$PY" --target "$DEST/site-packages" .
mkdir -p "$DEST/bin"
cp version.txt "$DEST/version.txt"

cat > "$DEST/bin/wowiso" <<'LAUNCHER'
#!/usr/bin/python3
# Self-contained wowiso launcher (bundled as a Tauri resource).
# sys.path is prepended with the sibling site-packages tree so the core and
# its dependencies resolve without any pipx/venv install on the host.
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "site-packages"))

from wowiso.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
LAUNCHER
chmod +x "$DEST/bin/wowiso"

# Smoke: must run under the system interpreter and report the stamped version.
"$DEST/bin/wowiso" version
