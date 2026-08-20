#!/usr/bin/env bash

GBFC_AGY_WRAPPER_SIGNATURE="# ANTIBESTFRIEND-AGY-WRAPPER"
GBFC_AGY_UPSTREAM_CFG="$GBFC_MANAGED/config/agy-upstream.json"

gbfc_is_wrapper() {
  local path="$1"
  [[ -f "$path" ]] && grep -qF "$GBFC_AGY_WRAPPER_SIGNATURE" "$path" 2>/dev/null
}

gbfc_discover_upstream_permission_flag() {
  local real_bin="$1"
  if [[ -x "$real_bin" ]] && "$real_bin" --help 2>&1 | grep -q -- "--dangerously-skip-permissions"; then
    printf '%s\n' "--dangerously-skip-permissions"
    return 0
  fi
  # Flag not found in --help output; fail instead of silently hardcoding
  gbfc_warn "upstream agy does not advertise --dangerously-skip-permissions; YOLO may not work with this version"
  printf '%s\n' "--dangerously-skip-permissions"
  return 1
}

gbfc_record_upstream_metadata() {
  local upstream="$1" target_real="$2"
  mkdir -p -- "$(dirname -- "$GBFC_AGY_UPSTREAM_CFG")"
  python3 - "$GBFC_AGY_UPSTREAM_CFG" "$upstream" "$target_real" "$(gbfc_now)" <<'PY'
import hashlib, json, os, sys
from pathlib import Path

cfg_path, upstream, real_path, now = sys.argv[1:5]
p = Path(real_path)
sha = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""
mode = oct(os.stat(real_path).st_mode) if os.path.exists(real_path) else ""

data = {
    "product": "antigravity-bestfriend",
    "upstreamSource": upstream,
    "realBinary": real_path,
    "installedAt": now,
    "sha256": sha,
    "mode": mode,
    "isSymlink": os.path.islink(upstream) if os.path.exists(upstream) else False,
}
Path(cfg_path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

gbfc_install_agy_yolo_wrapper() {
  local real_bin="$HOME/.local/bin/agy-real"
  local target_bin="$HOME/.local/bin/agy"
  local flag

  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_INSTALL yolo wrapper at $target_bin -> $real_bin"
    return 0
  fi

  mkdir -p -- "$HOME/.local/bin" "$GBFC_MANAGED/config"

  # If target_bin exists and is NOT a wrapper, preserve it to real_bin
  if [[ -f "$target_bin" ]] && ! gbfc_is_wrapper "$target_bin"; then
    if [[ ! -f "$real_bin" ]] || gbfc_is_wrapper "$real_bin" || ! cmp -s "$target_bin" "$real_bin"; then
      gbfc_info "New upstream agy version detected at $target_bin, promoting to $real_bin"
      mv -f "$target_bin" "$real_bin"
      chmod +x "$real_bin"
      gbfc_record_upstream_metadata "$target_bin" "$real_bin"
    fi
  fi

  # Ensure real_bin exists and is NOT a wrapper
  if [[ ! -x "$real_bin" ]] || gbfc_is_wrapper "$real_bin"; then
    local candidate
    while IFS= read -r candidate; do
      [[ -z "$candidate" || "$candidate" == "$target_bin" || "$candidate" == "$real_bin" ]] && continue
      if [[ -x "$candidate" ]] && ! gbfc_is_wrapper "$candidate"; then
        cp -a -- "$candidate" "$real_bin"
        chmod +x "$real_bin"
        gbfc_record_upstream_metadata "$candidate" "$real_bin"
        break
      fi
    done < <(which -a agy 2>/dev/null || true)
  fi

  if [[ ! -x "$real_bin" ]] || gbfc_is_wrapper "$real_bin"; then
    gbfc_die "cannot resolve real agy executable for wrapper"
  fi

  if ! flag="$(gbfc_discover_upstream_permission_flag "$real_bin")"; then
    gbfc_die "UNSUPPORTED_AGY_VERSION: upstream permission bypass flag unavailable"
  fi

  # Write hardened wrapper
  cat << 'WRAPPER_EOF' > "$target_bin"
#!/usr/bin/env bash
# ANTIBESTFRIEND-AGY-WRAPPER
# Hardened invocation wrapper for Google Antigravity CLI (agy)
set -euo pipefail

REAL_AGY="${REAL_AGY:-$HOME/.local/bin/agy-real}"
UPSTREAM_FLAG="__UPSTREAM_FLAG_PLACEHOLDER__"

if [[ ! -x "$REAL_AGY" ]] || grep -qF "# ANTIBESTFRIEND-AGY-WRAPPER" "$REAL_AGY" 2>/dev/null; then
  # Safe non-recursive fallback discovery
  FOUND=""
  while IFS= read -r candidate; do
    [[ -z "$candidate" || "$candidate" == "$HOME/.local/bin/agy" || "$candidate" == "$REAL_AGY" ]] && continue
    if [[ -x "$candidate" ]] && ! grep -qF "# ANTIBESTFRIEND-AGY-WRAPPER" "$candidate" 2>/dev/null; then
      FOUND="$candidate"
      break
    fi
  done < <(which -a agy 2>/dev/null || true)
  if [[ -n "$FOUND" ]]; then
    REAL_AGY="$FOUND"
  else
    printf 'ERROR: agy-real binary not found\n' >&2
    exit 1
  fi
fi

# Verify upstream still supports the permission flag
if ! "$REAL_AGY" --help 2>&1 | grep -q -- "$UPSTREAM_FLAG"; then
  printf 'WARNING: upstream agy may not support %s; passing through anyway\n' "$UPSTREAM_FLAG" >&2
fi

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
  # Inject the discovered flag into the wrapper
  sed -i "s|__UPSTREAM_FLAG_PLACEHOLDER__|$flag|" "$target_bin"
  chmod +x "$target_bin"
  gbfc_info "Hardened agy --yolo wrapper configured at $target_bin (translates to $flag)"
}

gbfc_wrapper_status() {
  local real_bin="$HOME/.local/bin/agy-real"
  local target_bin="$HOME/.local/bin/agy"

  printf 'target=%s\n' "$target_bin"
  if gbfc_is_wrapper "$target_bin"; then
    printf 'wrapper_ownership=OWNED_ANTIBESTFRIEND\n'
  else
    printf 'wrapper_ownership=NOT_WRAPPED\n'
  fi

  if [[ -x "$real_bin" && ! $(gbfc_is_wrapper "$real_bin") ]]; then
    local ver
    ver="$("$real_bin" --version 2>/dev/null | head -n 1 || echo "unknown")"
    printf 'real_binary=%s version=%s\n' "$real_bin" "$ver"
  else
    printf 'real_binary=MISSING_OR_CORRUPT\n'
  fi
}

gbfc_wrapper_repair() {
  gbfc_install_agy_yolo_wrapper
}

gbfc_wrapper_refresh() {
  local real_bin="$HOME/.local/bin/agy-real"
  local target_bin="$HOME/.local/bin/agy"
  local candidate=""

  while IFS= read -r c; do
    [[ -z "$c" || "$c" == "$target_bin" || "$c" == "$real_bin" ]] && continue
    if [[ -x "$c" ]] && ! gbfc_is_wrapper "$c"; then
      candidate="$c"
      break
    fi
  done < <(which -a agy 2>/dev/null || true)

  if [[ -n "$candidate" ]]; then
    gbfc_info "Discovered updated upstream agy at $candidate"
    cp -a -- "$candidate" "$real_bin"
    chmod +x "$real_bin"
    gbfc_record_upstream_metadata "$candidate" "$real_bin"
    gbfc_install_agy_yolo_wrapper
    gbfc_info "Wrapper refreshed successfully."
  else
    gbfc_info "No external upstream agy found; repairing current wrapper."
    gbfc_install_agy_yolo_wrapper
  fi
}
