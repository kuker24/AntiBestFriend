#!/usr/bin/env bash

gbfc_design_bank_ok() {
  local root="$1"
  [[ -n "$root" && -f "$root/Refero/bank/catalog.json" && -f "$root/motionsites/library/catalog.json" ]]
}

gbfc_discover_design_bank() {
  local candidate
  for candidate in \
    "${ANTIGRAVITY_DESIGN_BANK:-}" \
    "${GROK_DESIGN_BANK:-}" \
    "${CLAUDE_DESIGN_BANK:-}" \
    "$HOME/Downloads/LAB GITHUB/Design" \
    "$HOME/Design" \
    "$GBFC_MANAGED/design-bank"
  do
    if gbfc_design_bank_ok "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

gbfc_write_design_bank_config() {
  local root="$1" source="${2:-discover}"
  mkdir -p -- "$(dirname -- "$GBFC_DESIGN_BANK_CFG")"
  python3 - "$GBFC_DESIGN_BANK_CFG" "$root" "$source" "$(gbfc_now)" <<'PY'
import json, sys
from pathlib import Path
path, root, source, now = sys.argv[1:5]
payload = {
    "root": root,
    "catalogs": ["Refero/bank/catalog.json", "motionsites/library/catalog.json"],
    "discoveredAt": now,
    "source": source,
}
Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
}

gbfc_design_bank_download() {
  local dest="${1:-$HOME/Design}"
  local url expected stage archive
  url="$(gbfc_source_field design-bank artifactUrl)"
  expected="$(gbfc_source_field design-bank artifactSha256)"
  [[ -n "$url" && -n "$expected" ]] || return 1

  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_DOWNLOAD_DESIGN_BANK $url -> $dest"
    printf '%s\n' "$dest"
    return 0
  fi

  mkdir -p -- "$(dirname -- "$dest")"
  stage="$(mktemp -d)"
  archive="$stage/Design-bank.tgz"
  if ! gbfc_download "$url" "$archive" "$expected"; then
    rm -rf -- "$stage"
    return 1
  fi
  
  # Preflight archive validation
  local unsafe
  unsafe="$(tar -tzf "$archive" | grep -E '^/|\.\./' | head -n 1 || true)"
  if [[ -n "$unsafe" ]]; then
    gbfc_warn "Unsafe archive member detected: $unsafe"
    rm -rf -- "$stage"
    return 1
  fi

  # Atomic extraction + validation
  local extract_stage="$stage/extract"
  mkdir -p "$extract_stage"
  tar -xzf "$archive" -C "$extract_stage"
  
  # Check if nested (sometimes tarballs include the top level directory)
  local effective_root="$extract_stage"
  if gbfc_design_bank_ok "$extract_stage"; then
    effective_root="$extract_stage"
  else
    local nested
    nested="$(find "$extract_stage" -mindepth 1 -maxdepth 3 -type f -path '*/Refero/bank/catalog.json' | head -n 1 || true)"
    if [[ -n "$nested" ]]; then
      effective_root="$(cd -- "$(dirname -- "$nested")/../.." && pwd)"
    fi
  fi
  
  local target_dest="$dest"
  if [[ -d "$target_dest" ]]; then
    if ! gbfc_design_bank_ok "$target_dest"; then
      gbfc_warn "$target_dest exists but is NOT a valid Design Bank. Refusing to delete foreign data."
      target_dest="$GBFC_MANAGED/design-bank"
      gbfc_info "Redirecting Design Bank installation to $target_dest"
    fi
  fi

  if gbfc_design_bank_ok "$effective_root"; then
    rm -rf -- "$target_dest"
    mkdir -p -- "$(dirname -- "$target_dest")"
    mv -T -- "$effective_root" "$target_dest"
    rm -rf -- "$stage"
    printf '%s\n' "$target_dest"
    return 0
  fi
  
  rm -rf -- "$stage"
  return 1
}

gbfc_install_design_bank() {
  if [[ "$GBFC_SKIP_DESIGN_BANK" == 1 ]]; then
    gbfc_info "skipping design bank"
    return 0
  fi
  local root
  if root="$(gbfc_discover_design_bank)"; then
    if [[ "$GBFC_DRY_RUN" == 1 ]]; then
      gbfc_info "WOULD_DESIGN_BANK $root -> $GBFC_DESIGN_BANK_CFG"
      return 0
    fi
    gbfc_write_design_bank_config "$root" discover
    gbfc_info "Design Bank discovered: $root"
    return 0
  fi

  gbfc_info "Design Bank catalogs not found; downloading Release asset"
  if ! root="$(gbfc_design_bank_download "$HOME/Design")"; then
    gbfc_warn "Design Bank download failed; doctor will report NOT_CONFIGURED"
    return 0
  fi
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_DESIGN_BANK $root -> $GBFC_DESIGN_BANK_CFG"
    return 0
  fi
  gbfc_write_design_bank_config "$root" download
  gbfc_info "Design Bank installed: $root"
}

gbfc_design_bank_rediscover() {
  local root
  root="$(gbfc_discover_design_bank)" || gbfc_die "no valid Design Bank catalogs found"
  gbfc_write_design_bank_config "$root" rediscover
  gbfc_info "Design Bank rediscovered: $root"
}
