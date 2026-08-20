#!/usr/bin/env bash

GBFC_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
GBFC_ROOT="$(cd -- "$GBFC_LIB_DIR/.." && pwd)"
GBFC_WORKSPACE="$GBFC_ROOT"
GBFC_VENDOR_SOURCE="${GBFC_VENDOR_SOURCE:-$GBFC_ROOT}"
GBFC_MANAGED="${GBFC_MANAGED:-$HOME/.gemini/antigravity-bestfriend}"
gbfc_resolve_plugin_dir() {
  local candidates=(
    "$HOME/.gemini/config/plugins/antigravity-bestfriend"
    "$HOME/.gemini/antigravity-cli/plugins/antigravity-bestfriend"
  )
  for c in "${candidates[@]}"; do
    if [[ -d "$c" ]]; then
      printf '%s\n' "$c"
      return 0
    fi
  done
  # Fallback to stage mirror if uninstalled
  printf '%s\n' "$GBFC_MANAGED/stage/antigravity-bestfriend"
}

GBFC_AGY_CONFIG="${GBFC_AGY_CONFIG:-$HOME/.gemini/config}"
GBFC_GLOBAL_ROUTER="${GBFC_GLOBAL_ROUTER:-$HOME/.gemini/GEMINI.md}"
GBFC_MANIFEST="$GBFC_MANAGED/MANIFEST.json"
GBFC_OWNERSHIP="$GBFC_MANAGED/config/mcp-ownership.json"
GBFC_DESIGN_BANK_CFG="$GBFC_MANAGED/config/design-bank.json"
GBFC_CBM_BIN="$GBFC_MANAGED/components/codebase-memory/bin/codebase-memory-mcp"
GBFC_CDP="$GBFC_MANAGED/bin/agy-chromium-cdp"
GBFC_DISPATCH="$GBFC_MANAGED/bin/agy-bestfriend"
GBFC_CONTEXT_GUARD="$GBFC_MANAGED/bin/agy-context-guard"
GBFC_CONTEXT_GUARD_CFG="$GBFC_MANAGED/config/context-guard.json"
GBFC_PRODUCT="antigravity-bestfriend"
GBFC_MARKER=".gbf-agy-owned.json"
GBFC_DRY_RUN="${GBFC_DRY_RUN:-0}"
GBFC_REPAIR="${GBFC_REPAIR:-0}"
GBFC_SKIP_TOOLS="${GBFC_SKIP_TOOLS:-0}"
GBFC_SKIP_DESIGN_BANK="${GBFC_SKIP_DESIGN_BANK:-0}"
GBFC_LOCK_FD="${GBFC_LOCK_FD:-}"
GBFC_BACKUP_STAMP="${GBFC_BACKUP_STAMP:-}"

gbfc_info() { printf '%s\n' "$*"; }
gbfc_warn() { printf 'WARNING: %s\n' "$*" >&2; }
gbfc_error() { printf 'ERROR: %s\n' "$*" >&2; }
gbfc_die() { gbfc_error "$*"; exit 1; }
gbfc_have() { command -v "$1" >/dev/null 2>&1; }

gbfc_backup_root() { printf '%s/backups\n' "$GBFC_MANAGED"; }
gbfc_stage_root() { printf '%s/stage\n' "$GBFC_MANAGED"; }

gbfc_product_version() {
  tr -d '[:space:]' <"$GBFC_ROOT/VERSION"
}

gbfc_source_commit() {
  if [[ -d "$GBFC_ROOT/.git" ]]; then
    git -C "$GBFC_ROOT" rev-parse HEAD
    return 0
  fi
  # No .git directory; check for packaged commit stamp
  if [[ -f "$GBFC_MANAGED/config/source-commit.txt" ]]; then
    cat "$GBFC_MANAGED/config/source-commit.txt"
  else
    printf '%s\n' "unknown"
  fi
}

gbfc_sha256_file() {
  sha256sum -- "$1" | awk '{print $1}'
}

gbfc_load_allowlist() {
  GBFC_SKILL_NAMES=()
  local line allow="$GBFC_VENDOR_SOURCE/vendor/skill-allowlist.txt"
  [[ -f "$allow" ]] || allow="$GBFC_ROOT/vendor/skill-allowlist.txt"
  [[ -f "$allow" ]] || allow="$GBFC_MANAGED/vendor/skill-allowlist.txt"
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    GBFC_SKILL_NAMES+=("$line")
  done <"$allow"
}

gbfc_load_rule_allowlist() {
  GBFC_RULE_NAMES=()
  local line allow="$GBFC_VENDOR_SOURCE/vendor/rule-allowlist.txt"
  [[ -f "$allow" ]] || allow="$GBFC_ROOT/vendor/rule-allowlist.txt"
  [[ -f "$allow" ]] || allow="$GBFC_MANAGED/vendor/rule-allowlist.txt"
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    GBFC_RULE_NAMES+=("$line")
  done <"$allow"
}

gbfc_now() {
  date -u +"%Y%m%d%H%M%SZ"
}
