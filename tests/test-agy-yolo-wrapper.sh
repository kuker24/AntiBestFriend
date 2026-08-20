#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# Mock agy-real
tmp="$(mktemp -d)"
cat << 'MOCK_EOF' > "$tmp/agy-real"
#!/usr/bin/env bash
echo "RECEIVED: $@"
MOCK_EOF
chmod +x "$tmp/agy-real"

REAL_AGY="$tmp/agy-real" bash -c '
args=()
for arg in "--yolo" "-p" "hello"; do
  case "$arg" in
    --yolo|-y) args+=("--dangerously-skip-permissions") ;;
    *) args+=("$arg") ;;
  esac
done
'"$tmp/agy-real"' "${args[@]}"
' | grep -q "RECEIVED: --dangerously-skip-permissions -p hello"

rm -rf "$tmp"
echo "Agy yolo wrapper test passed."
