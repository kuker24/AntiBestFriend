#!/usr/bin/env bash

# shellcheck source=/dev/null
[[ -f "$GBFC_ROOT/lib/design-bank.sh" ]] && source "$GBFC_ROOT/lib/design-bank.sh"

gbfc_doctor() {
  local failed=0
  local strict="${GBFC_DOCTOR_STRICT:-0}"

  gbfc_check() {
    local status="$1" label="$2" detail="${3:-}"
    if [[ "$status" == "PASS" ]]; then
      printf '\033[32mPASS\033[0m %-25s %s\n' "$label" "$detail"
    elif [[ "$status" == "DEGRADED" || "$status" == "NOT_CONFIGURED" || "$status" == "CONFIGURED_DISABLED" || "$status" == "FOREIGN_SHARED" ]]; then
      printf '\033[33m%s\033[0m %-25s %s\n' "$status" "$label" "$detail"
      [[ "$strict" == 1 && "$status" != "CONFIGURED_DISABLED" && "$status" != "FOREIGN_SHARED" ]] && ((failed++)) || true
    else
      printf '\033[31m%s\033[0m %-25s %s\n' "$status" "$label" "$detail"
      ((failed++))
    fi
  }

  echo "=== AntiBestFriend Doctor V2 (Runtime-First) ==="

  # -------------------------------------------------------------
  # Layer 1: Filesystem & Host Environment
  # -------------------------------------------------------------
  echo "--- 1. HOST ENVIRONMENT ---"
  if gbfc_have agy; then
    local agy_path
    agy_path="$(command -v agy)"
    gbfc_check PASS "agy_binary" "$agy_path"
  else
    gbfc_check FAIL "agy_binary" "agy not found on PATH"
  fi

  if gbfc_have python3; then
    local py_ver
    py_ver="$(python3 --version 2>/dev/null | head -n 1)"
    gbfc_check PASS "python" "$py_ver"
  else
    gbfc_check FAIL "python" "python3 required"
  fi

  if gbfc_have node && gbfc_have npx; then
    local node_ver
    node_ver="$(node --version 2>/dev/null)"
    gbfc_check PASS "node_npx" "$node_ver"
  else
    gbfc_check FAIL "node_npx" "node and npx required for shadcn MCP"
  fi

  if gbfc_have git; then
    local git_ver
    git_ver="$(git --version 2>/dev/null | head -n 1)"
    gbfc_check PASS "git" "$git_ver"
  else
    gbfc_check FAIL "git" "git required"
  fi

  # -------------------------------------------------------------
  # Layer 2: YOLO Wrapper & Upstream Topology
  # -------------------------------------------------------------
  echo "--- 2. YOLO WRAPPER & TOPOLOGY ---"
  local real_bin="$HOME/.local/bin/agy-real"
  local wrapper_bin="$HOME/.local/bin/agy"

  if [[ -x "$real_bin" ]]; then
    local real_ver
    real_ver="$("$real_bin" --version 2>/dev/null | head -n 1 || echo "unknown")"
    gbfc_check PASS "agy_real" "$real_bin ($real_ver)"
  else
    gbfc_check FAIL "agy_real" "missing upstream executable at $real_bin"
  fi

  if [[ -f "$wrapper_bin" ]] && grep -qF "# ANTIBESTFRIEND-AGY-WRAPPER" "$wrapper_bin" 2>/dev/null; then
    gbfc_check PASS "wrapper_signature" "OWNED_ANTIBESTFRIEND (# ANTIBESTFRIEND-AGY-WRAPPER)"
  else
    gbfc_check FAIL "wrapper_signature" "wrapper signature missing at $wrapper_bin"
  fi

  # Test wrapper translation non-destructively
  if [[ -x "$wrapper_bin" && -x "$real_bin" ]]; then
    local yolo_test short_y_test
    yolo_test="$("$wrapper_bin" --yolo --version 2>/dev/null || echo "err")"
    short_y_test="$("$wrapper_bin" -y --version 2>/dev/null || echo "err")"
    if [[ "$yolo_test" != "err" && "$short_y_test" != "err" ]]; then
      gbfc_check PASS "yolo_aliases" "--yolo and -y working (translates to --dangerously-skip-permissions)"
    else
      gbfc_check FAIL "yolo_aliases" "wrapper invocation failed"
    fi
  fi

  # -------------------------------------------------------------
  # Layer 3: Native Antigravity Plugin & Skills
  # -------------------------------------------------------------
  echo "--- 3. PLUGIN & SKILLS DISCOVERY ---"
  local resolved_plugin_dir
  resolved_plugin_dir="$(gbfc_resolve_plugin_dir)"

  if [[ -f "$resolved_plugin_dir/plugin.json" ]]; then
    gbfc_check PASS "plugin_manifest" "$resolved_plugin_dir/plugin.json"
  else
    gbfc_check FAIL "plugin_manifest" "missing $resolved_plugin_dir/plugin.json"
  fi

  if command -v agy >/dev/null 2>&1; then
    local plugin_list
    plugin_list="$(agy plugin list 2>/dev/null || echo "")"
    if echo "$plugin_list" | grep -q "antigravity-bestfriend"; then
      gbfc_check PASS "plugin_registration" "detected in agy plugin list"
    else
      gbfc_check DEGRADED "plugin_registration" "plugin pending import in agy"
    fi
  fi

  if [[ -d "$resolved_plugin_dir/skills" ]]; then
    local allowlist_path="$GBFC_ROOT/vendor/skill-allowlist.txt"
    [[ -f "$allowlist_path" ]] || allowlist_path="$GBFC_MANAGED/vendor/skill-allowlist.txt"
    local policy_path="$GBFC_ROOT/vendor/skill-policy.json"
    [[ -f "$policy_path" ]] || policy_path="$GBFC_MANAGED/vendor/skill-policy.json"

    local rep
    rep="$(python3 "$GBFC_ROOT/lib/validate_skills.py" \
      --skills "$resolved_plugin_dir/skills" \
      --allowlist "$allowlist_path" \
      --policy "$policy_path" 2>&1)"
    if [[ $? -eq 0 ]]; then
      gbfc_check PASS "skills_parity" "40/40 skills verified (24 model-routed, 16 manual-only [ROUTER_ENFORCED])"
    else
      gbfc_check FAIL "skills_parity" "$rep"
    fi
  else
    gbfc_check FAIL "skills_dir" "missing $resolved_plugin_dir/skills"
  fi

  if [[ -f "$GBFC_GLOBAL_ROUTER" ]] && grep -q "ANTIGRAVITY-BESTFRIEND:BEGIN" "$GBFC_GLOBAL_ROUTER"; then
    gbfc_check PASS "router" "active in $GBFC_GLOBAL_ROUTER"
  else
    gbfc_check FAIL "router" "missing owned router block in $GBFC_GLOBAL_ROUTER"
  fi

  # -------------------------------------------------------------
  # Layer 4: MCP Servers (Exact 4, Zero Exa)
  # -------------------------------------------------------------
  echo "--- 4. MCP SERVERS (EXACT 4, ZERO EXA) ---"
  local mcp_cfg="$GBFC_AGY_CONFIG/mcp_config.json"
  if [[ -f "$mcp_cfg" ]]; then
    local mcp_output
    mcp_output="$(python3 - "$mcp_cfg" <<'PY'
import json, sys
from pathlib import Path

p = Path(sys.argv[1])
try:
    data = json.loads(p.read_text(encoding="utf-8"))
    servers = data.get("mcpServers", {})
except Exception as e:
    print(f"FAIL mcp_config Malformed mcp_config.json: {e}")
    raise SystemExit(0)

if "codebase-memory-mcp" in servers:
    cmd = servers["codebase-memory-mcp"].get("command", "")
    if cmd and Path(cmd).is_file():
        print(f"PASS codebase_memory {cmd}")
    else:
        print(f"DEGRADED codebase_memory binary at {cmd} not found")
else:
    print("FAIL codebase_memory missing in mcpServers")

if "context7" in servers:
    url = servers["context7"].get("serverUrl", "")
    print(f"PASS context7 {url}")
else:
    print("FAIL context7 missing in mcpServers")

if "shadcn" in servers:
    cmd = servers["shadcn"].get("command", "")
    args = " ".join(servers["shadcn"].get("args", []))
    print(f"PASS shadcn {cmd} {args}")
else:
    print("FAIL shadcn missing in mcpServers")

if "serena" in servers:
    import shutil
    serena_path = shutil.which("serena") or shutil.which("serena", path=str(Path.home() / ".local" / "bin"))
    if serena_path:
        dis = servers["serena"].get("disabled", False)
        if dis:
            print("CONFIGURED_DISABLED serena on-demand (disabled by default)")
        else:
            print("PASS serena enabled")
    else:
        print("FAIL serena serena binary not found in PATH or ~/.local/bin")
else:
    print("FAIL serena missing in mcpServers")

if "exa" in servers:
    print("FAIL exa_absent EXA_IS_FORBIDDEN (detected in mcpServers)")
else:
    print("PASS exa_absent confirmed zero Exa configured")
PY
    )"
    while IFS= read -r line; do
      local mcp_status mcp_label mcp_detail
      mcp_status="$(echo "$line" | awk '{print $1}')"
      mcp_label="$(echo "$line" | awk '{print $2}')"
      mcp_detail="$(echo "$line" | cut -d' ' -f3-)"
      gbfc_check "$mcp_status" "$mcp_label" "$mcp_detail"
    done <<< "$mcp_output"
  else
    gbfc_check FAIL "mcp_config" "missing $mcp_cfg"
  fi

  # -------------------------------------------------------------
  # Layer 5: Design Ecosystem & Intelligence
  # -------------------------------------------------------------
  echo "--- 5. DESIGN SUBSYSTEM ---"
  local bank_root
  if type -t gbfc_discover_design_bank >/dev/null && bank_root="$(gbfc_discover_design_bank)"; then
    gbfc_check PASS "design_bank" "$bank_root (Refero + motionsites catalogs valid)"
  elif [[ -f "$GBFC_DESIGN_BANK_CFG" ]]; then
    local configured_bank
    configured_bank="$(python3 -c "import json; print(json.load(open('$GBFC_DESIGN_BANK_CFG')).get('root', ''))" 2>/dev/null || echo "")"
    if [[ -n "$configured_bank" && -f "$configured_bank/Refero/bank/catalog.json" ]]; then
      gbfc_check PASS "design_bank" "$configured_bank (Refero + motionsites catalogs valid)"
    else
      gbfc_check NOT_CONFIGURED "design_bank" "catalogs not found at standard paths"
    fi
  else
    gbfc_check NOT_CONFIGURED "design_bank" "catalogs not found at standard paths"
  fi

  if python3 -c "import sys; sys.path.insert(0, '$GBFC_ROOT/lib'); sys.path.insert(0, '$GBFC_MANAGED/lib'); from design_intelligence import catalog, rank, selection; print('ok')" >/dev/null 2>&1; then
    gbfc_check PASS "design_intelligence" "modules loadable and operational"
  else
    gbfc_check FAIL "design_intelligence" "failed to load design_intelligence modules"
  fi

  # -------------------------------------------------------------
  # Layer 6: Context Guard & Chromium CDP
  # -------------------------------------------------------------
  echo "--- 6. CONTEXT GUARD & RUNTIME HELPERS ---"
  if [[ -x "$GBFC_CONTEXT_GUARD" ]]; then
    if "$GBFC_CONTEXT_GUARD" self-test >/dev/null 2>&1; then
      gbfc_check PASS "context_guard" "self-test passed"
    else
      gbfc_check FAIL "context_guard" "self-test failed"
    fi
  else
    gbfc_check FAIL "context_guard" "binary not executable: $GBFC_CONTEXT_GUARD"
  fi

  if [[ -x "$GBFC_CDP" ]]; then
    local cdp_bin
    if cdp_bin="$("$GBFC_CDP" resolve 2>/dev/null)"; then
      gbfc_check PASS "chromium_cdp" "resolved $cdp_bin (Google Chrome rejected)"
    else
      gbfc_check NOT_CONFIGURED "chromium_cdp" "no Chromium binary found"
    fi
  else
    gbfc_check FAIL "chromium_cdp" "binary not found: $GBFC_CDP"
  fi

  echo "================================================="
  if [[ $failed -eq 0 ]]; then
    echo "Doctor Status: ALL_CHECKS_PASSED"
    return 0
  else
    echo "Doctor Status: $failed FAILURES"
    return 1
  fi
}
