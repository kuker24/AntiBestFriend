#!/usr/bin/env bash

gbfc_source_field() {
  local id="$1" field="$2"
  python3 - "$GBFC_VENDOR_SOURCE/vendor/sources.json" "$id" "$field" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(data.get("sources", {}).get(sys.argv[2], {}).get(sys.argv[3], ""))
PY
}

gbfc_download() {
  local url="$1" dest="$2" expected="$3"
  if ! curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 --output "$dest" "$url"; then
    return 1
  fi
  local got
  got="$(gbfc_sha256_file "$dest")"
  [[ "$got" == "$expected" ]] || return 1
  return 0
}

gbfc_install_codebase_memory() {
  local version artifact expected target stage existing_bin artifact_source
  version="$(gbfc_source_field codebase-memory version)"
  artifact="$(gbfc_source_field codebase-memory artifactUrl)"
  expected="$(gbfc_source_field codebase-memory artifactSha256)"
  target="$GBFC_CBM_BIN"
  existing_bin="$HOME/.claude/grokbestfriend-claude/components/codebase-memory/bin/codebase-memory-mcp"
  artifact_source="official"

  if [[ -x "$target" ]] && "$target" --version 2>/dev/null | grep -Fq "$version"; then
    gbfc_info "codebase-memory $version already at $target"
    printf '%s\n' "$artifact_source" >"$GBFC_MANAGED/config/cbm-source.txt"
    return 0
  fi

  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_INSTALL codebase-memory $version -> $target"
    return 0
  fi

  if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
    gbfc_die "codebase-memory pinned artifact is Linux x86_64 only"
  fi

  mkdir -p -- "$(dirname -- "$target")" "$GBFC_MANAGED/config"

  if [[ -x "$existing_bin" ]] && "$existing_bin" --version 2>/dev/null | grep -Fq "$version"; then
    gbfc_info "using verified local cache for codebase-memory: $existing_bin"
    cp -a -- "$existing_bin" "$target"
    chmod 755 -- "$target"
    artifact_source="local-verified"
  else
    stage="$(mktemp -d)"
    if gbfc_download "$artifact" "$stage/cbm.tgz" "$expected"; then
      tar -xzf "$stage/cbm.tgz" -C "$stage"
      local bin="$stage/codebase-memory-mcp"
      if [[ ! -f "$bin" ]]; then
        bin="$(find "$stage" -type f -name 'codebase-memory-mcp' | head -n 1)"
      fi
      [[ -n "$bin" && -f "$bin" ]] || gbfc_die "codebase-memory binary missing from archive"
      chmod 755 -- "$bin"
      "$bin" --version 2>/dev/null | grep -Fq "$version" || gbfc_die "codebase-memory version mismatch"
      install -m 755 "$bin" "$target"
      artifact_source="official"
      rm -rf -- "$stage"
    else
      rm -rf -- "$stage"
      gbfc_die "codebase-memory download failed"
    fi
  fi

  printf '%s\n' "$artifact_source" >"$GBFC_MANAGED/config/cbm-source.txt"
  gbfc_info "codebase-memory $version installed ($artifact_source)"
}

gbfc_install_helper_bins() {
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_INSTALL helpers"
    return 0
  fi
  mkdir -p -- "$GBFC_MANAGED/bin" "$HOME/.local/bin"
  install -m 755 "$GBFC_ROOT/runtime/agy-chromium-cdp" "$GBFC_CDP"
  install -m 755 "$GBFC_ROOT/bin/agy-bestfriend" "$GBFC_DISPATCH"
  install -m 755 "$GBFC_ROOT/bin/agy-context-guard" "$GBFC_CONTEXT_GUARD"

  # Link into ~/.local/bin for global accessibility
  ln -sf "$GBFC_DISPATCH" "$HOME/.local/bin/agy-bestfriend"
  ln -sf "$GBFC_CDP" "$HOME/.local/bin/agy-chromium-cdp"
  ln -sf "$GBFC_CONTEXT_GUARD" "$HOME/.local/bin/agy-context-guard"

  # Native agy wrapper installation
  gbfc_install_agy_yolo_wrapper
}

gbfc_install_agy_yolo_wrapper() {
  local real_bin="$HOME/.local/bin/agy-real"
  local target_bin="$HOME/.local/bin/agy"

  # If agy-real does not exist and agy is an ELF binary, move agy to agy-real
  if [[ ! -f "$real_bin" && -f "$target_bin" ]]; then
    if file "$target_bin" | grep -q "ELF"; then
      mv -f "$target_bin" "$real_bin"
      chmod +x "$real_bin"
    fi
  fi

  # Install agy wrapper supporting --yolo
  cat << 'WRAPPER_EOF' > "$target_bin"
#!/usr/bin/env bash
set -euo pipefail

REAL_AGY="${REAL_AGY:-$HOME/.local/bin/agy-real}"
if [[ ! -x "$REAL_AGY" ]]; then
  # Fallback discovery
  REAL_AGY="$(which -a agy-real 2>/dev/null | head -n 1 || true)"
fi

if [[ ! -x "$REAL_AGY" ]]; then
  printf 'ERROR: agy-real binary not found at %s\n' "$REAL_AGY" >&2
  exit 1
fi

args=()
for arg in "$@"; do
  case "$arg" in
    --yolo|-y)
      args+=("--dangerously-skip-permissions")
      ;;
    *)
      args+=("$arg")
      ;;
  esac
done

exec "$REAL_AGY" "${args[@]}"
WRAPPER_EOF
  chmod +x "$target_bin"
  gbfc_info "Native agy --yolo wrapper configured at $target_bin"
}
