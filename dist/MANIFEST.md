# WowISO dist/ MANIFEST — v1.3.80595

Full stamped set built 2026-08-28. Windows legs built natively on Windows 11
(MSVC); Linux legs built natively in WSL2 Ubuntu 24.04 on ext4
(`~/forgejo/wowiso`), core bundled from `/usr/bin/python3` 3.12 via
`scripts/bundle-core.sh`.

## v1.3.80595 artifacts

| SHA256 | Bytes | File |
|---|---:|---|
| `593d8da92a40e18224a064f92db4bd869fd8dbc8578531d80d4855a7898fa0be` | 260284416 | `wowiso-v1.3.80595-windows-x64.msi` |
| `98758663cdd48697ce9af528a0d1c313b67865976bacab28b2e5d24f160d24b3` | 262911683 | `wowiso-v1.3.80595-windows-x64-setup.exe` |
| `83948831768e2096e532f550c7d38ace4a509fa8c5b2f3b758b8136d852d22c5` | 7300026 | `wowiso-v1.3.80595-linux-amd64.deb` |
| `cb8ea3c92f60f2a9818fba3383ef19dc662f4d2f8e8f255e7938b34315786b81` | 7377185 | `wowiso-v1.3.80595-linux-amd64.rpm` |
| `db500381606a7e12fa3da46bd174f53bbb770b9e8437871a5986138daa58dd76` | 81467896 | `wowiso-v1.3.80595-linux-amd64.AppImage` |
| `2f81bc21ecd8cb43396e2db4ed5e82d3dad4df2eda8beb68f48355ae56bb2c80` | 35652 | `wowiso-1.3.80595-py3-none-any.whl` |
| `b869b0d2c996a9fe71d46ebbc889310534629a88d7b22ef4ff72a9de8163d5e4` | 34682 | `wowiso-1.3.80595.tar.gz` |

## Windows installers — Microsoft Store compatibility notes

Built with `tauri.microsoftstore.conf.json` overlay:
`bundle.windows.webviewInstallMode = offlineInstaller` (WebView2 standalone
embedded — no download at install time) and `bundle.publisher` set. MSI
ProductVersion is `1.3.805.95` (WiX caps the patch field at 65535, so BUILD
80595 maps to `805.95` via `tauri.windows.conf.json`; display version remains
1.3.80595).

Silent install arguments (recorded for the future Store/winget listing — not
submitted anywhere):

- MSI: `msiexec /i wowiso-v1.3.80595-windows-x64.msi /qn`
- NSIS: `wowiso-v1.3.80595-windows-x64-setup.exe /S`

Windows runtime hosts the Python core in WSL2 Ubuntu 24.04 (`wsl.exe -d
Ubuntu-24.04 -- wowiso …`); Linux packages are self-contained (`core-dist/`
resource).

## Historical stamps retained

- `wowiso-v1.2.74933-linux-amd64.{deb,rpm,AppImage}` (git-LFS pointers)
- `wowiso-1.1.74918-py3-none-any.whl`, `wowiso-1.1.74918.tar.gz`
