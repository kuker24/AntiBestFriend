#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP"
mkdir -p "$HOME/.local/bin"

# Source wrapper lib
source "$ROOT/lib/common.sh"
source "$ROOT/lib/wrapper.sh"
REAL_BIN="$HOME/.local/bin/agy-real"
cat << 'MOCK_EOF' > "$REAL_BIN"
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
  echo "1.1.17"
  exit 0
fi
if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: agy [OPTIONS]"
  echo "  --dangerously-skip-permissions  Skip permission checks"
  exit 0
fi
echo "RECEIVED: $@"
MOCK_EOF
chmod +x "$REAL_BIN"

# Install production wrapper
gbfc_install_agy_yolo_wrapper

WRAPPER="$HOME/.local/bin/agy"
[[ -x "$WRAPPER" ]] || { echo "FAIL: wrapper not installed"; exit 1; }

# 1. Normal invocation
OUT="$(REAL_AGY="$REAL_BIN" "$WRAPPER" -p "hello world")"
[[ "$OUT" == "RECEIVED: -p hello world" ]] || { echo "FAIL normal invocation: $OUT"; exit 1; }

# 2. --yolo translation
OUT="$(REAL_AGY="$REAL_BIN" "$WRAPPER" --yolo -p "fix bug")"
[[ "$OUT" == "RECEIVED: --dangerously-skip-permissions -p fix bug" ]] || { echo "FAIL --yolo: $OUT"; exit 1; }

# 3. -y translation
OUT="$(REAL_AGY="$REAL_BIN" "$WRAPPER" -y -p "fix bug")"
[[ "$OUT" == "RECEIVED: --dangerously-skip-permissions -p fix bug" ]] || { echo "FAIL -y: $OUT"; exit 1; }

# 4. Duplicate --yolo deduplication
OUT="$(REAL_AGY="$REAL_BIN" "$WRAPPER" --yolo --yolo -p "test")"
[[ "$OUT" == "RECEIVED: --dangerously-skip-permissions -p test" ]] || { echo "FAIL duplicate yolo: $OUT"; exit 1; }

# 5. Native flag + --yolo deduplication
OUT="$(REAL_AGY="$REAL_BIN" "$WRAPPER" --dangerously-skip-permissions --yolo -p "test")"
[[ "$OUT" == "RECEIVED: --dangerously-skip-permissions -p test" ]] || { echo "FAIL mixed yolo: $OUT"; exit 1; }

# 6. Spaces in arguments
OUT="$(REAL_AGY="$REAL_BIN" "$WRAPPER" --yolo -p "arg with spaces and 'quotes'")"
[[ "$OUT" == "RECEIVED: --dangerously-skip-permissions -p arg with spaces and 'quotes'" ]] || { echo "FAIL quotes: $OUT"; exit 1; }

echo "PASS: test_yolo_wrapper"
