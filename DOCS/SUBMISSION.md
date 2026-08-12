# Submission runbook — Microsoft Store + winget

> **Scope of this document:** the concrete steps to publish wowiso to
> the **Microsoft Store** (app) and the **winget** repository (package manifest).
> Most of these steps require **human-owned credentials and a Partner Center
> account** and **cannot be executed from inside the repo**. This file exists so
> the path is captured, ordered, and checkable. It is a planning artifact, not
> an automated pipeline.
>
> Prerequisite for **every** step below: Phase 1 of `CHECKLIST.md` is shipped —
> there must be a working `wowiso` CLI and a functional Windows build (see
> `DOCS/ARCHITECTURE/windows-store-wsl-bridge.md`) before there is anything to
> submit.

```
Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved.
```

## 0. Hard prerequisites (not done today)

- [ ] **Phase 1 shipped** — `wowiso` CLI captures/builds end-to-end on Linux
      (M1–M8 in `CHECKLIST.md`). Today: **0 LOC of feature code.**
- [ ] **WSL2 bridge built** (Phase 3.5) — a functional Windows MSIX exists.
- [ ] **Partner Center account** (individual or organization), active, paid
      one-time registration. **Human step — cannot be done from the repo.**
- [ ] **Signing identity** — for Store submission, the Store re-signs on
      ingestion, so an EV cert is not strictly required; for winget/test,
      a self-signed dev cert suffices locally.

## 1. Reserve the app identity (Partner Center) — *human*

1. Sign in to **Partner Center** → *Apps and games* → *New product* →
   *MSIX or PWA app* (we ship an MSIX).
2. **Reserve the product name** (e.g. `wowiso`). Reservation yields:
   - `Package/Identity/Name`
   - `Package/Identity/Publisher`
3. Record both — they are baked into the MSIX manifest at build time.

> Naming note: "Ubuntu" is a Canonical trademark. The reserved name and all
> Store listing copy must respect the trademark disclaimer already in `NOTICE`
> ("Ubuntu … trademark of Canonical"). Prefer a name that does not imply
> Canonical endorsement.

## 2. Build the MSIX (repo, once §1 identity exists)

- `gui/src-tauri/tauri.conf.json` →
  `bundle.windows.targets: ["msi","msix"]`, with the Partner-Center identity
  injected into the MSIX app manifest.
- Version stamp from `version.py::current()`:
  `wowiso-v<version>-windows-x64.msix`.
- Local test-sign the MSIX with a dev cert; install via
  `Add-AppxPackage` to smoke-test on a clean Windows + WSL2 machine.
- Acceptance gate: the GUI launches, the WSL-setup screen provisions the
  distro, and a trivial REPO capture→build runs end-to-end producing an ISO
  surfaced onto the Windows filesystem.

## 3. Store listing assets (repo + human)

- Screenshots: mode/emit pickers, tree-picker, build-progress, WSL-setup,
  About (the M7.1 Stitch screens). At least one per required Store size.
- Description, release notes, privacy URL (the app shells to WSL and writes to
  removable media — declare this honestly).
- **Age rating questionnaire** — answer truthfully; a developer/OS-install tool
  with no user-generated content typically lands at a low tier, but the
  questionnaire determines it, not a guess.
- Capabilities declaration: `runFullTrust` (full-trust packaged desktop app).

## 4. Submit for certification (Partner Center) — *human*

1. *Start submission* → upload the signed MSIX.
2. Attach listing (§3), choose availability markets, set pricing (free is the
   natural choice for an open-source dev tool).
3. Submit → **certification review** (automated + manual; hours to days).
4. On approval → published. On failure → read the report, fix, re-upload.

> The Store re-signs the package on ingestion with its own identity; do not be
> alarmed that the published signature differs from the upload signature.

## 5. winget repository manifest (alternative / complement) — *human, GitHub PR*

winget (`microsoft/winget-pkgs`) distributes via a manifest PR, not Partner
Center. Use this if you want `winget install wowiso` to work without
the Store.

1. Once the **MSI** (not MSIX — winget consumes the MSI/EXE installer) is
   published at a stable URL with a known SHA256:
2. Use `wingetcreate new <publisher>/<Name>` against the installer URL, or
   hand-author a YAML manifest under
   `manifests/<first-letter>/<Publisher>/<Name>/<version>/`.
3. Fields: `PackageIdentifier`, `PackageVersion` (from `version.py::current()`,
   the stamped `MAJOR.MINOR.BUILD` is already a valid winget quad, e.g. `1.1.74918`).
   `Installers[].InstallerUrl` + `InstallerSha256`, `InstallerType: wix` (MSI).
4. Open a PR; the winget bot validates the manifest + installer. Merged =
   available in the next winget repo sync.

## 6. What "completed submission" means — and the irreducible remainder

A submission is **completed** when either:

- (Store) the MSIX passes certification and is **published** in the Store, or
- (winget) the manifest PR is **merged** into `winget-pkgs`.

Both terminators require actions outside this repo: a Partner Center account
with a published package, or a merged upstream PR against a Microsoft-owned
repository. **No agent session can reach either terminator on its own** — they
are gated on human-owned identity and a Microsoft-side review/merge.

### What an agent session CAN deliver (submission-readiness)

- The functional app + Windows build (Phase 1 + Phase 3.5).
- The MSIX packaging config, identity-ready.
- The Store listing assets + accurate capabilities/age-rating input.
- This runbook, executed up to the credential-gated upload step.

That is the deliverable ceiling for in-repo work; everything in §4 and §5
beyond the PR/upload is human.
