#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Create mock real binary
REAL_BIN="$TMP/agy-real"
cat << 'MOCK_EOF' > "$REAL_BIN"
#!/usr/bin/env bash
echo "RECEIVED: $@"
MOCK_EOF
chmod +x "$REAL_BIN"

# Create production wrapper
WRAPPER="$TMP/agy"
cat << 'WRAPPER_EOF' > "$WRAPPER"
#!/usr/bin/env bash
# ANTIBESTFRIEND-AGY-WRAPPER
set -euo pipefail

REAL_AGY="${REAL_AGY}"
UPSTREAM_FLAG="--dangerously-skip-permissions"

args=()
has_permission_bypass=0

for arg in "$@"; do
  case "$arg" in
    --yolo|-y)
      if [[ $has_permission_bypass -eq 0 ]]; then
        args+=("$UPSTREAM_FLAG")
        has_permission_bypass=1
      fi
      ;;
    --dangerously-skip-permissions)
      if [[ $has_permission_bypass -eq 0 ]]; then
        args+=("$arg")
        has_permission_bypass=1
      fi
      ;;
    *)
      args+=("$arg")
      ;;
  esac
done

exec "$REAL_AGY" "${args[@]}"
WRAPPER_EOF
chmod +x "$WRAPPER"

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
