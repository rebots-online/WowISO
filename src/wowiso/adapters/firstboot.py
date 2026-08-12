# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
"""First-boot restore orchestrator script. §3.9 frozen contract.

Renders ``/wowiso/wowiso-restore`` — a bash script that cloud-init invokes
on first boot. It reads ``/wowiso/manifest.json`` and, for each adapter in
``adapter_order``, runs ``install → apply_config → verify`` in order. In
``WOWISO_DRY_RUN=1`` mode it only logs the ordered calls (used by tests and
pre-flight checks). The per-adapter restore work is delegated to a bundled
``wowiso-adapter-<name>`` helper that the payload stages alongside this script.
"""
from __future__ import annotations

from ..manifest import Manifest


def render_firstboot_script(manifest: Manifest) -> str:
    """Render the bash first-boot orchestrator for ``manifest.adapter_order``."""
    steps: list[str] = []
    for name in manifest.adapter_order:
        steps.append(f'  _wowiso_step "{name}"')
    steps_blob = "\n".join(steps) if steps else "  : # no adapters"
    return (
        "#!/usr/bin/env bash\n"
        "# /wowiso/wowiso-restore — invoked by cloud-init on first boot.\n"
        "# Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.\n"
        "set -eu\n"
        'MANIFEST="${WOWISO_MANIFEST:-/wowiso/manifest.json}"\n'
        'PAYLOAD="${WOWISO_PAYLOAD:-/wowiso}"\n\n'
        "_wowiso_step() {\n"
        '  local name="$1"\n'
        '  if [ "${WOWISO_DRY_RUN:-0}" = "1" ]; then\n'
        '    echo "wowiso-restore: install   $name"\n'
        '    echo "wowiso-restore: apply     $name"\n'
        '    echo "wowiso-restore: verify    $name"\n'
        "    return 0\n"
        "  fi\n"
        '  /wowiso/wowiso-adapter-"$name" install   "$MANIFEST" "$PAYLOAD"\n'
        '  /wowiso/wowiso-adapter-"$name" apply     "$MANIFEST" "$PAYLOAD"\n'
        '  /wowiso/wowiso-adapter-"$name" verify    "$MANIFEST" "$PAYLOAD"\n'
        "}\n\n"
        f"main() {{\n{steps_blob}\n}}\n\n"
        "main \"$@\"\n"
    )
