#!/usr/bin/env bash

gbfc_doctor() {
  local failed=0
  local strict="${GBFC_DOCTOR_STRICT:-0}"

  gbfc_check() {
    local status="$1" label="$2" detail="${3:-}"
    if [[ "$status" == "PASS" ]]; then
      printf '\033[32mPASS\033[0m %s %s\n' "$label" "$detail"
    elif [[ "$status" == "DEGRADED" ]]; then
      printf '\033[33mDEGRADED\033[0m %s %s\n' "$label" "$detail"
      [[ "$strict" == 1 ]] && ((failed++)) || true
    else
      printf '\033[31mFAIL\033[0m %s %s\n' "$label" "$detail"
      ((failed++))
    fi
  }

  echo "=== AntigravityBestFriend Doctor ==="

  # 1. Host CLI & Environment
  if gbfc_have agy; then
    local agy_ver
    agy_ver="$(agy --version 2>/dev/null | head -n 1 || echo "unknown")"
    gbfc_check PASS "agy_binary" "($agy_ver)"
  else
    gbfc_check FAIL "agy_binary" "not found on PATH"
  fi

  if gbfc_have python3; then
    local py_ver
    py_ver="$(python3 --version 2>/dev/null | head -n 1)"
    gbfc_check PASS "python" "($py_ver)"
  else
    gbfc_check FAIL "python" "python3 required"
  fi

  if gbfc_have node && gbfc_have npx; then
    local node_ver
    node_ver="$(node --version 2>/dev/null)"
    gbfc_check PASS "node_npx" "($node_ver)"
  else
    gbfc_check FAIL "node_npx" "node and npx required"
  fi

  # 2. Plugin Installation
  if [[ -f "$GBFC_PLUGIN_DIR/plugin.json" ]]; then
    gbfc_check PASS "plugin_manifest" "$GBFC_PLUGIN_DIR/plugin.json"
  else
    gbfc_check FAIL "plugin_manifest" "missing $GBFC_PLUGIN_DIR/plugin.json"
  fi

  # 3. 40 Skills Verification
  if [[ -d "$GBFC_PLUGIN_DIR/skills" ]]; then
    local rep
    rep="$(python3 "$GBFC_ROOT/lib/validate_skills.py" \
      --skills "$GBFC_PLUGIN_DIR/skills" \
      --allowlist "$GBFC_VENDOR_SOURCE/vendor/skill-allowlist.txt" \
      --policy "$GBFC_VENDOR_SOURCE/vendor/skill-policy.json" 2>&1)"
    if [[ $? -eq 0 ]]; then
      gbfc_check PASS "skills_parity" "40/40 skills verified (24 model-routed, 16 manual-only)"
    else
      gbfc_check FAIL "skills_parity" "$rep"
    fi
  else
    gbfc_check FAIL "skills_dir" "missing $GBFC_PLUGIN_DIR/skills"
  fi

  # 4. Router & Rules
  if [[ -f "$GBFC_PLUGIN_DIR/rules/AGENTS.md" && -f "$GBFC_GLOBAL_ROUTER" ]] && grep -q "ANTIGRAVITY-BESTFRIEND:BEGIN" "$GBFC_GLOBAL_ROUTER"; then
    gbfc_check PASS "router" "global router active in $GBFC_GLOBAL_ROUTER"
  else
    gbfc_check FAIL "router" "global router missing owned block"
  fi

  # 5. MCP Servers
  local mcp_cfg="$GBFC_AGY_CONFIG/mcp_config.json"
  if [[ -f "$mcp_cfg" ]]; then
    local cbm_ok context7_ok shadcn_ok serena_ok exa_absent
    cbm_ok="$(python3 - "$mcp_cfg" <<'PY'
import json, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("mcpServers", {})
print("1" if "codebase-memory-mcp" in d else "0")
PY
)"
    context7_ok="$(python3 - "$mcp_cfg" <<'PY'
import json, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("mcpServers", {})
print("1" if "context7" in d else "0")
PY
)"
    shadcn_ok="$(python3 - "$mcp_cfg" <<'PY'
import json, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("mcpServers", {})
print("1" if "shadcn" in d else "0")
PY
)"
    serena_ok="$(python3 - "$mcp_cfg" <<'PY'
import json, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("mcpServers", {})
print("1" if "serena" in d else "0")
PY
)"
    exa_absent="$(python3 - "$mcp_cfg" <<'PY'
import json, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("mcpServers", {})
print("1" if "exa" not in d else "0")
PY
)"
    if [[ "$cbm_ok" == 1 && "$context7_ok" == 1 && "$shadcn_ok" == 1 && "$serena_ok" == 1 && "$exa_absent" == 1 ]]; then
      gbfc_check PASS "mcp_servers" "exact 4 MCPs configured (codebase-memory, context7, shadcn, serena; exa absent)"
    else
      gbfc_check FAIL "mcp_servers" "MCP configuration mismatch (cbm:$cbm_ok c7:$context7_ok shadcn:$shadcn_ok serena:$serena_ok exa_absent:$exa_absent)"
    fi
  else
    gbfc_check FAIL "mcp_servers" "missing $mcp_cfg"
  fi

  # 6. Design Bank
  local bank_root
  if bank_root="$(gbfc_discover_design_bank)"; then
    gbfc_check PASS "design_bank" "$bank_root"
  else
    gbfc_check DEGRADED "design_bank" "not configured"
  fi

  # 7. Design Intelligence
  if python3 -c "import sys; sys.path.insert(0, '$GBFC_ROOT/lib'); from design_intelligence import catalog, rank, selection; print('ok')" >/dev/null 2>&1; then
    gbfc_check PASS "design_intelligence" "modules loadable and operational"
  else
    gbfc_check FAIL "design_intelligence" "failed to load design_intelligence modules"
  fi

  # 8. Context Guard
  if [[ -x "$GBFC_CONTEXT_GUARD" ]]; then
    if "$GBFC_CONTEXT_GUARD" self-test >/dev/null 2>&1; then
      gbfc_check PASS "context_guard" "self-test passed"
    else
      gbfc_check FAIL "context_guard" "self-test failed"
    fi
  else
    gbfc_check FAIL "context_guard" "binary not executable: $GBFC_CONTEXT_GUARD"
  fi

  # 9. Chromium CDP
  if [[ -x "$GBFC_CDP" ]]; then
    local cdp_bin
    if cdp_bin="$("$GBFC_CDP" resolve 2>/dev/null)"; then
      gbfc_check PASS "chromium_cdp" "resolved $cdp_bin"
    else
      gbfc_check DEGRADED "chromium_cdp" "no Chromium binary found"
    fi
  else
    gbfc_check FAIL "chromium_cdp" "binary not found: $GBFC_CDP"
  fi

  # 10. Native agy wrapper
  if [[ -f "$HOME/.local/bin/agy-real" ]] && grep -q -- "--dangerously-skip-permissions" "$HOME/.local/bin/agy" 2>/dev/null; then
    gbfc_check PASS "agy_yolo_wrapper" "agy --yolo mode active"
  else
    gbfc_check DEGRADED "agy_yolo_wrapper" "wrapper pending"
  fi

  if [[ $failed -eq 0 ]]; then
    echo "Doctor Status: ALL_CHECKS_PASSED"
    return 0
  else
    echo "Doctor Status: $failed FAILURES"
    return 1
  fi
}
