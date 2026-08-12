#!/usr/bin/env bash
# =============================================================================
# scripts/update-version.sh — WowISO canonical version stamper.
#
# Source of truth: ~/Admin-Manual/versioning/update-version.sh (the WORKING
# canonical variant). DO NOT re-derive this logic. Scheme (BUILD_CONVENTIONS):
#   MAJOR = manual milestone (edit version.txt by hand, once per milestone)
#   MINOR = auto-bumped heartbeat (resets to 0 when MAJOR changes)
#   BUILD = epoch-minutes % 100000
#   versionName = MAJOR.MINOR.BUILD    e.g. 1.1.74911
#   versionCode = MAJOR*100000 + MINOR (BUILD excluded — Play needs monotonic)
#
# Operator fix (2026-08-11): a successful build consumes the current version, so
# the codebase can no longer be attested clean at that version. Therefore:
#   USAGE / BUILD FLOW
#     1. `scripts/update-version.sh stamp`   # materialize version.txt → manifests (NO bump); build this version
#     2. build (cargo tauri build / pip build)
#     3. on SUCCESS: `scripts/update-version.sh`   # default = bump MINOR, so the tree advances PAST the built version
#   The default invocation ALWAYS bumps (the invariant: the bump lives INSIDE the
#   stamper). `stamp` is the only non-bumping path, used pre-build.
#
# version.txt holds the padded DISPLAY version (5-digit BUILD). Semver/PEP440
# manifest fields (Cargo.toml, tauri.conf.json, pyproject.toml) take the UNPADDED
# BUILD so they remain valid when BUILD < 10000.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

PRODUCT_NAME="WowISO"
INTERNAL_NAME="wowiso"
PACKAGE_NAME="mba.robin.wowiso"

MODE="${1:-bump}"
LOCK_FILE="$PROJECT_ROOT/release.lock"

compute() {
  if [ -f "$LOCK_FILE" ]; then
    echo "[update-version] Using frozen release.lock values" >&2
    # shellcheck source=/dev/null
    source "$LOCK_FILE"                                   # sets MAJOR, MINOR, BUILD_NUM
  else
    CURRENT_VERSION=$(tr -d '[:space:]' < version.txt 2>/dev/null || echo "1.0.0")
    CURRENT_MAJOR=$(echo "$CURRENT_VERSION" | cut -d. -f1)
    CURRENT_MINOR=$(echo "$CURRENT_VERSION" | cut -d. -f2)
    MAJOR="$CURRENT_MAJOR"                                # manual milestone in version.txt
    if [ "$MODE" = "stamp" ]; then
      CURRENT_BUILD=$(echo "$CURRENT_VERSION" | cut -d. -f3)
      BUILD_NUM="${CURRENT_BUILD#0}" ; [ -n "$BUILD_NUM" ] || BUILD_NUM=0
      MINOR="$CURRENT_MINOR"                              # stamp = no bump
    else
      MINOR=$((CURRENT_MINOR + 1))                        # THE heartbeat — never remove
      BUILD_NUM=$(( $(date +%s) / 60 % 100000 ))
    fi
  fi

  BUILD_PADDED="$(printf '%05d' "${BUILD_NUM}")"
  DISPLAY_VERSION="${MAJOR}.${MINOR}.${BUILD_PADDED}"
  SEMVER_VERSION="${MAJOR}.${MINOR}.${BUILD_NUM}"          # unpadded → valid semver/PEP440
  VERSION_CODE=$(( MAJOR * 100000 + MINOR ))
}

write_files() {
  echo "${DISPLAY_VERSION}" > version.txt
  cat > version.json << EOF
{
  "version": "${DISPLAY_VERSION}",
  "semver": "${SEMVER_VERSION}",
  "versionBase": "${MAJOR}.${MINOR}",
  "buildNumber": "${BUILD_PADDED}",
  "versionCode": ${VERSION_CODE},
  "buildDate": "$(date -Iseconds)",
  "productName": "${PRODUCT_NAME}",
  "internalName": "${INTERNAL_NAME}",
  "packageName": "${PACKAGE_NAME}"
}
EOF

  # manifest stamps — guarded, semver/PEP440-safe (unpadded BUILD)
  [ -f pyproject.toml ] && \
    sed -i '0,/^version *= *"[^"]*"/s//version = "'"${SEMVER_VERSION}"'"/' pyproject.toml
  [ -f gui/package.json ] && command -v jq >/dev/null && {
    jq --arg v "${SEMVER_VERSION}" '.version = $v' gui/package.json > gui/package.json.tmp
    mv gui/package.json.tmp gui/package.json
  }
  [ -f gui/src-tauri/tauri.conf.json ] && \
    sed -i 's/"version": "[^"]*"/"version": "'"${SEMVER_VERSION}"'"/' gui/src-tauri/tauri.conf.json
  [ -f gui/src-tauri/Cargo.toml ] && \
    sed -i '0,/^version *= *"[^"]*"/s//version = "'"${SEMVER_VERSION}"'"/' gui/src-tauri/Cargo.toml

  export PROJECT_VERSION="${DISPLAY_VERSION}" PROJECT_SEMVER="${SEMVER_VERSION}" PROJECT_VERSION_CODE="${VERSION_CODE}"
  echo "[update-version] ${MODE}: ${DISPLAY_VERSION}  (semver ${SEMVER_VERSION}, code ${VERSION_CODE})"
}

compute
write_files
