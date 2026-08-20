#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_STAGE="$(mktemp -d)"
trap 'rm -rf "$TEMP_STAGE"' EXIT

if ! command -v agy >/dev/null 2>&1 && [[ ! -x "$HOME/.local/bin/agy-real" && ! -x "$HOME/.local/bin/agy" ]]; then
  mkdir -p "$HOME/.local/bin"
  cat << 'MOCK_AGY' > "$HOME/.local/bin/agy"
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then echo "1.1.17"; exit 0; fi
if [[ "${1:-}" == "--help" ]]; then echo "  --dangerously-skip-permissions"; exit 0; fi
if [[ "${1:-}" == "plugin" ]]; then
  if [[ "${2:-}" == "install" ]]; then
    mkdir -p "$HOME/.gemini/config/plugins/antigravity-bestfriend"
    cp -a -- "$3/"* "$HOME/.gemini/config/plugins/antigravity-bestfriend/"
  elif [[ "${2:-}" == "list" ]]; then echo "antigravity-bestfriend"
  elif [[ "${2:-}" == "uninstall" ]]; then rm -rf "$HOME/.gemini/config/plugins/antigravity-bestfriend"
  fi
  exit 0
fi
MOCK_AGY
  chmod +x "$HOME/.local/bin/agy"
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "=== Testing Self-Contained Managed Runtime ==="

# Ensure latest installation is committed
"$ROOT/install.sh" >/dev/null

# Move source out of the way to prove independence
TEMP_REPO="$(mktemp -d)/repo"
mv "$ROOT" "$TEMP_REPO"

# Re-register cleanup to restore repo
trap 'mv "$TEMP_REPO" "$ROOT" && rm -rf "$(dirname "$TEMP_REPO")" "$TEMP_STAGE"' EXIT

# Verify CLI tools can execute independently from anywhere without depending on source git clone
agy-bestfriend doctor >/dev/null
agy-bestfriend skills list >/dev/null
agy-bestfriend mcp status >/dev/null
agy-bestfriend design-bank status >/dev/null
agy-bestfriend wrapper status >/dev/null

# Verify uninstall works without source repo
agy-bestfriend uninstall >/dev/null

echo "PASS: test_self_contained_runtime"
