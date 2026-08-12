# DOCS/ARCHITECTURE/

AST-level representations of the system. Keep in sync with `ARCHITECTURE.md` and
`CHECKLIST.md` whenever the design changes.

| File | What | Flavor |
|------|------|--------|
| `pipeline.mmd` / `pipeline.puml` | capture → build → emit → boot pipeline | mermaid + plantuml |
| `modes.mmd` | REPO / LIVE / IMAGE build modes | mermaid |
| `firstboot-sequence.mmd` | first-boot cloud-init sequence (REPO) | mermaid sequence |
| `manifest-erd.mmd` / `manifest-erd.puml` | payload manifest entity relationships | mermaid + plantuml |
| `windows-store-wsl-bridge.md` / `.mmd` | Windows Store viability — Tauri2 GUI ⇄ WSL2-hosted core | prose + mermaid (DESIGN, not yet built) |

Render: `mmdc -i <file>.mmd -o <file>.png` (mermaid) / `plantuml <file>.puml`.
Generated PNGs should be committed alongside (CLAUDE.md: graphics saved with repo).
