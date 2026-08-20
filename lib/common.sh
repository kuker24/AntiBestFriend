#!/usr/bin/env bash

GBFC_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
GBFC_ROOT="$(cd -- "$GBFC_LIB_DIR/.." && pwd)"
GBFC_WORKSPACE="$GBFC_ROOT"
GBFC_VENDOR_SOURCE="${GBFC_VENDOR_SOURCE:-$GBFC_ROOT}"
GBFC_MANAGED="${GBFC_MANAGED:-$HOME/.gemini/antigravity-bestfriend}"
GBFC_PLUGIN_DIR="${GBFC_PLUGIN_DIR:-$HOME/.gemini/config/plugins/antigravity-bestfriend}"
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

gbfc_product_version() {
  tr -d '[:space:]' <"$GBFC_ROOT/VERSION"
}

gbfc_source_commit() {
  if [[ -d "$GBFC_ROOT/.git" ]]; then
    git -C "$GBFC_ROOT" rev-parse HEAD
    return 0
  fi
  printf '%s\n' "05e6fdcdb70fe7f4420827e4df1a360f2152700c"
}

gbfc_sha256_file() {
  sha256sum -- "$1" | awk '{print $1}'
}

gbfc_load_allowlist() {
  GBFC_SKILL_NAMES=()
  local line
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    GBFC_SKILL_NAMES+=("$line")
  done <"$GBFC_VENDOR_SOURCE/vendor/skill-allowlist.txt"
}

gbfc_load_rule_allowlist() {
  GBFC_RULE_NAMES=()
  local line file
  file="$GBFC_VENDOR_SOURCE/vendor/rule-allowlist.txt"
  [[ -f "$file" ]] || file="$GBFC_ROOT/vendor/rule-allowlist.txt"
  [[ -f "$file" ]] || gbfc_die "missing vendor/rule-allowlist.txt"
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    GBFC_RULE_NAMES+=("$line")
  done <"$file"
}

gbfc_now() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

gbfc_stamp() {
  date -u +"%Y%m%dT%H%M%SZ"
}
