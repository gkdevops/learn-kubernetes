#!/usr/bin/env bash
#
# Local counterpart of the "Security scan" GitHub workflow.
#
#   - Trivy     : IaC misconfiguration (bundles kube-linter KSV-*, Kubescape,
#                 Checkov and friends).
#   - Kubescape : framework controls (NIST) + an overall compliance score.
#
# Both tools are downloaded at their LATEST release, so this script never
# pins a stale scanner. CI uses the vendors' own actions instead
# (.github/workflows/security-scan.yml); both render the same report through
# scripts/report.py.
#
# Usage:
#   bash scripts/scan.sh                  # download tools if missing, then scan
#   FORCE_UPDATE=1 bash scripts/scan.sh   # always re-download the scanners
#   SCAN_OUT=/tmp bash scripts/scan.sh    # write the artifacts elsewhere
#
# Artifacts (git-ignored): security-report.md, trivy.json, kubescape.json
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$REPO_ROOT/scripts/tools"
OUT_DIR="${SCAN_OUT:-$REPO_ROOT}"
REPORT="$OUT_DIR/security-report.md"

mkdir -p "$TOOLS_DIR"

# ---------------------------------------------------------------- OS + assets
case "$(uname -s)" in
  Linux)                 TRIVY_ASSET="Linux-64bit";   KS_ASSET="linux_amd64";   TRIVY_EXT="tar.gz" ;;
  Darwin)                TRIVY_ASSET="Darwin-64bit";  KS_ASSET="darwin_amd64";  TRIVY_EXT="tar.gz" ;;
  MINGW*|MSYS*|CYGWIN*) TRIVY_ASSET="windows-64bit"; KS_ASSET="windows_amd64"; TRIVY_EXT="zip" ;;
  *) echo "unsupported OS: $(uname -s)" >&2; exit 1 ;;
esac

latest_tag() {
  # deliberately jq-free: no hard dependency beyond curl + grep
  curl -fsSL "https://api.github.com/repos/$1/releases/latest" \
    | grep -o '"tag_name": *"[^"]*"' | head -1 | cut -d'"' -f4
}

extract() { # extract <archive> <dest-dir>
  case "$1" in
    *.zip)
      if command -v unzip >/dev/null 2>&1; then unzip -oq "$1" -d "$2"
      elif command -v powershell >/dev/null 2>&1; then
        powershell -NoProfile -Command "Expand-Archive -Path '$1' -DestinationPath '$2' -Force"
      else echo "need unzip or PowerShell to extract $1" >&2; exit 1
      fi ;;
    *) tar -xzf "$1" -C "$2" ;;
  esac
}

already_have() { # already_have <path>
  [[ -z "${FORCE_UPDATE:-}" && -f "$TOOLS_DIR/$1" ]]
}

install_trivy() {
  local ver url tmp
  if already_have trivy.exe; then return; fi
  if already_have trivy; then return; fi
  ver="$(latest_tag aquasecurity/trivy)"; ver="${ver#v}"
  url="https://github.com/aquasecurity/trivy/releases/download/v${ver}/trivy_${ver}_${TRIVY_ASSET}.${TRIVY_EXT}"
  tmp="$(mktemp -d)"
  echo "==> trivy: downloading v${ver}"
  curl -fsSL -o "$tmp/trivy" "$url"
  extract "$tmp/trivy" "$TOOLS_DIR"
  rm -rf "$tmp"
  chmod +x "$TOOLS_DIR/trivy" 2>/dev/null || true
}

install_kubescape() {
  local ver url tmp
  if already_have kubescape.exe; then return; fi
  if already_have kubescape; then return; fi
  ver="$(latest_tag kubescape/kubescape)"; ver="${ver#v}"
  url="https://github.com/kubescape/kubescape/releases/download/v${ver}/kubescape_${ver}_${KS_ASSET}.tar.gz"
  tmp="$(mktemp -d)"
  echo "==> kubescape: downloading v${ver}"
  curl -fsSL -o "$tmp/kubescape.tar.gz" "$url"
  extract "$tmp/kubescape.tar.gz" "$TOOLS_DIR"
  rm -rf "$tmp"
  chmod +x "$TOOLS_DIR/kubescape" 2>/dev/null || true
}

trivy_bin="$TOOLS_DIR/trivy.exe";     [[ -f "$trivy_bin" ]]     || trivy_bin="$TOOLS_DIR/trivy"
kubescape_bin="$TOOLS_DIR/kubescape.exe"; [[ -f "$kubescape_bin" ]] || kubescape_bin="$TOOLS_DIR/kubescape"

install_trivy
install_kubescape

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python  >/dev/null 2>&1; then PY=python
else echo "python 3 is required to render the report" >&2; exit 1; fi

echo "==> trivy:     $("$trivy_bin" --version | head -1)"
echo "==> kubescape: $("$kubescape_bin" version 2>/dev/null | head -1 | sed 's/.*: //')"

# ------------------------------------------------------------------- scanning
echo "==> trivy: scanning manifests"
"$trivy_bin" config --quiet --format json --output "$OUT_DIR/trivy.json" "$REPO_ROOT"

echo "==> kubescape: scanning manifests"
"$kubescape_bin" scan "$REPO_ROOT" \
  --format json --output "$OUT_DIR/kubescape.json" --submit=false >/dev/null

# -------------------------------------------------------------------- report
echo "==> rendering report"
"$PY" "$REPO_ROOT/scripts/report.py" \
  --trivy "$OUT_DIR/trivy.json" \
  --kubescape "$OUT_DIR/kubescape.json" \
  -o "$REPORT"

echo
cat "$REPORT"
echo "==> wrote $REPORT"