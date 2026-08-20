#!/usr/bin/env bash

gbfc_render_template() {
  local src="$1" dest="$2"
  python3 - "$src" "$dest" "$GBFC_MANAGED" "$GBFC_CBM_BIN" "$GBFC_CONTEXT_GUARD" <<'PY'
import sys
from pathlib import Path

src_p, dest_p, managed, cbm, cg = sys.argv[1:6]
text = Path(src_p).read_text(encoding="utf-8")
text = text.replace("@MANAGED_ROOT@", managed)
text = text.replace("@CODEBASE_MEMORY_BIN@", cbm)
text = text.replace("@CONTEXT_GUARD_BIN@", cg)
dest_path = Path(dest_p)
dest_path.parent.mkdir(parents=True, exist_ok=True)
dest_path.write_text(text, encoding="utf-8")
PY
}

gbfc_write_manifest() {
  local tmp
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_WRITE $GBFC_MANIFEST"
    return 0
  fi
  mkdir -p -- "$GBFC_MANAGED/config"
  tmp="$(mktemp "$GBFC_MANAGED/.manifest.XXXXXX")"
  python3 - "$tmp" "$GBFC_ROOT" "$GBFC_MANAGED" "$GBFC_CBM_BIN" \
    "$(gbfc_product_version)" "$(gbfc_source_commit)" "$(gbfc_now)" \
    "${GBFC_DESIGN_BANK_CFG:-}" <<'PY'
import hashlib, json, sys
from pathlib import Path

target, root, managed, cbm, version, commit, now, bank_cfg = sys.argv[1:9]

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "0"*64

allow = Path(managed, "vendor/skill-allowlist.txt")
if not allow.is_file():
    allow = Path(root, "vendor/skill-allowlist.txt")
skills = [line.strip() for line in allow.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]

hashes = {}
for rel in (
    "vendor/skill-allowlist.txt",
    "vendor/skill-policy.json",
    "vendor/rule-allowlist.txt",
    "vendor/mcp-policy.json",
    "vendor/sources.json",
    "vendor/inventory.json",
):
    src = Path(managed, rel)
    if not src.is_file():
        src = Path(root, rel)
    hashes[rel] = sha(src)

cbm_source = "unknown"
src_file = Path(managed, "config/cbm-source.txt")
if src_file.is_file():
    cbm_source = src_file.read_text(encoding="utf-8").strip()

design = {}
if bank_cfg and Path(bank_cfg).is_file():
    try:
        design = json.loads(Path(bank_cfg).read_text(encoding="utf-8"))
    except Exception:
        pass

ownership = {}
own_path = Path(managed, "config/mcp-ownership.json")
if own_path.is_file():
    try:
        ownership = json.loads(own_path.read_text(encoding="utf-8"))
    except Exception:
        pass

payload = {
    "product": "antigravity-bestfriend",
    "productVersion": version,
    "installed_at": now,
    "source": {
        "repo": "https://github.com/kuker24/AntiBestFriend",
        "commit": commit,
        "branch": "main",
    },
    "testedWithAgy": "1.1.17",
    "hashes": hashes,
    "skills": [f"{Path.home()}/.gemini/config/plugins/antigravity-bestfriend/skills/{name}" for name in skills],
    "mcpOwnership": ownership,
    "designBank": design,
    "codebaseMemory": {
        "path": cbm,
        "artifactSource": cbm_source,
        "version": "0.9.0",
    },
    "managedRoot": managed,
    "contextGuard": {
        "runtime": str(Path(managed, "bin/agy-context-guard")),
        "config": str(Path(managed, "config/context-guard.json")),
    },
}
Path(target).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
  chmod 600 "$tmp"
  mv -f -- "$tmp" "$GBFC_MANIFEST"
}

gbfc_ensure_mcp() {
  local name
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_MCP ensure codebase-memory-mcp context7 shadcn serena; exa absent"
    return 0
  fi
  python3 "$GBFC_ROOT/lib/mcp.py" classify-all --policy "$GBFC_ROOT/vendor/mcp-policy.json" \
    >"$GBFC_MANAGED/config/mcp-classify.json"

  for name in codebase-memory-mcp context7 shadcn; do
    gbfc_info "Configuring MCP $name..."
    python3 "$GBFC_ROOT/lib/mcp.py" add --name "$name" --policy "$GBFC_ROOT/vendor/mcp-policy.json" \
      || gbfc_die "Failed to add MCP $name"
  done

  # Serena configured disabled by default (on-demand)
  python3 "$GBFC_ROOT/lib/mcp.py" add --name "serena" --policy "$GBFC_ROOT/vendor/mcp-policy.json" \
    || gbfc_die "Failed to configure serena MCP"
}

gbfc_install_context_guard() {
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_CONTEXT_GUARD $GBFC_MANAGED/lib/context_guard"
    return 0
  fi
  mkdir -p -- "$GBFC_MANAGED/lib" "$GBFC_MANAGED/bin" "$GBFC_MANAGED/config" "$GBFC_MANAGED/context-cache"
  chmod 700 -- "$GBFC_MANAGED/context-cache"
  rm -rf -- "$GBFC_MANAGED/lib/context_guard"
  cp -a -- "$GBFC_ROOT/lib/context_guard" "$GBFC_MANAGED/lib/context_guard"
  find "$GBFC_MANAGED/lib/context_guard" -type d -name __pycache__ -prune -exec rm -rf -- {} +
  find "$GBFC_MANAGED/lib/context_guard" -type f -name '*.pyc' -delete
  install -m 755 "$GBFC_ROOT/bin/agy-context-guard" "$GBFC_CONTEXT_GUARD"

  if [[ ! -f "$GBFC_CONTEXT_GUARD_CFG" ]]; then
    cp -a -- "$GBFC_ROOT/templates/context-guard.example.json" "$GBFC_CONTEXT_GUARD_CFG"
    chmod 600 -- "$GBFC_CONTEXT_GUARD_CFG"
  fi

  PYTHONPATH="$GBFC_MANAGED/lib${PYTHONPATH:+:$PYTHONPATH}" GBFC_MANAGED="$GBFC_MANAGED" \
    "$GBFC_CONTEXT_GUARD" self-test >/dev/null \
    || gbfc_die "context-guard self-test failed"
  gbfc_info "CONTEXT_GUARD_READY"
}

gbfc_package_self_contained_runtime() {
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_PACKAGE_RUNTIME -> $GBFC_MANAGED"
    return 0
  fi
  mkdir -p -- "$GBFC_MANAGED/lib" "$GBFC_MANAGED/scripts" "$GBFC_MANAGED/vendor" "$GBFC_MANAGED/rules" "$GBFC_MANAGED/templates" "$GBFC_MANAGED/runtime" "$GBFC_MANAGED/overlays"

  # Copy lib
  cp -a -- "$GBFC_ROOT/lib/"*.sh "$GBFC_MANAGED/lib/" 2>/dev/null || true
  cp -a -- "$GBFC_ROOT/lib/"*.py "$GBFC_MANAGED/lib/" 2>/dev/null || true
  rm -rf -- "$GBFC_MANAGED/lib/design_intelligence"
  cp -a -- "$GBFC_ROOT/lib/design_intelligence" "$GBFC_MANAGED/lib/"
  find "$GBFC_MANAGED/lib" -type d -name __pycache__ -prune -exec rm -rf -- {} +
  find "$GBFC_MANAGED/lib" -type f -name '*.pyc' -delete

  # Copy scripts, templates, vendor metadata, rules, overlays
  cp -a -- "$GBFC_ROOT/scripts/"* "$GBFC_MANAGED/scripts/" 2>/dev/null || true
  cp -a -- "$GBFC_ROOT/templates/"* "$GBFC_MANAGED/templates/" 2>/dev/null || true
  cp -a -- "$GBFC_ROOT/vendor/"* "$GBFC_MANAGED/vendor/" 2>/dev/null || true
  cp -a -- "$GBFC_ROOT/rules/"* "$GBFC_MANAGED/rules/" 2>/dev/null || true
  cp -a -- "$GBFC_ROOT/overlays/"* "$GBFC_MANAGED/overlays/" 2>/dev/null || true
  cp -a -- "$GBFC_ROOT/runtime/"* "$GBFC_MANAGED/runtime/" 2>/dev/null || true
  cp -a -- "$GBFC_ROOT/VERSION" "$GBFC_MANAGED/VERSION"
  cp -a -- "$GBFC_ROOT/uninstall.sh" "$GBFC_MANAGED/uninstall.sh"

  # Record source commit for self-contained runtime
  mkdir -p -- "$GBFC_MANAGED/config"
  gbfc_source_commit > "$GBFC_MANAGED/config/source-commit.txt"

  gbfc_info "Self-contained managed runtime packaged in $GBFC_MANAGED"
}

gbfc_check_fault() {
  local state="$1"
  if [[ -n "${GBFC_FAIL_AT:-}" && "$GBFC_FAIL_AT" == "$state" ]]; then
    gbfc_die "SIMULATED_FAULT at state $state"
  fi
}

gbfc_run_install() {
  [[ -d "$GBFC_ROOT/vendor/skills" ]] || gbfc_die "vendor skills missing: $GBFC_ROOT/vendor/skills"
  [[ -f "$GBFC_ROOT/vendor/skill-allowlist.txt" ]] || gbfc_die "missing skill-allowlist"
  gbfc_have python3 || gbfc_die "python3 required"
  gbfc_have node || gbfc_die "node required for shadcn pin"
  gbfc_have npx || gbfc_die "npx required for shadcn pin"

  # Discover or recover agy
  if ! gbfc_have agy && [[ -x "$HOME/.local/bin/agy-real" ]]; then
    gbfc_install_agy_yolo_wrapper
  fi
  gbfc_have agy || gbfc_have agy-real || gbfc_die "agy CLI required"

  gbfc_lock_begin
  gbfc_tx_check_stale
  gbfc_tx_set_state PREPARING
  gbfc_check_fault PREPARING

  mkdir -p -- "$GBFC_MANAGED/config" "$GBFC_MANAGED/tx" "$GBFC_MANAGED/bin" "$GBFC_MANAGED/components" "$GBFC_PLUGIN_DIR"
  gbfc_backup_owned
  gbfc_tx_set_state BACKED_UP
  gbfc_check_fault BACKED_UP

  gbfc_package_self_contained_runtime
  gbfc_install_codebase_memory
  gbfc_install_serena
  gbfc_install_helper_bins
  gbfc_tx_set_state WRAPPER_CONFIGURED
  gbfc_check_fault WRAPPER_CONFIGURED

  gbfc_stage_skills
  gbfc_tx_set_state SKILLS_CONFIGURED
  gbfc_check_fault SKILLS_CONFIGURED

  gbfc_swap_skills
  gbfc_install_router
  gbfc_tx_set_state RULES_CONFIGURED
  gbfc_check_fault RULES_CONFIGURED

  gbfc_install_design_bank
  gbfc_tx_set_state DESIGN_CONFIGURED
  gbfc_check_fault DESIGN_CONFIGURED

  gbfc_ensure_mcp
  gbfc_tx_set_state MCP_CONFIGURED
  gbfc_check_fault MCP_CONFIGURED

  gbfc_install_context_guard
  gbfc_tx_set_state HOOKS_CONFIGURED
  gbfc_check_fault HOOKS_CONFIGURED

  gbfc_write_manifest
  gbfc_tx_set_state VERIFIED
  gbfc_check_fault VERIFIED

  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "dry-run complete"
    gbfc_lock_end
    return 0
  fi

  if ! gbfc_doctor; then
    gbfc_warn "doctor reported FAIL during install; leaving txn for recover"
    gbfc_lock_end
    return 1
  fi

  gbfc_tx_set_state COMMITTED
  gbfc_tx_clear
  gbfc_lock_end
  gbfc_info "Installation COMMITTED successfully."
}
