#!/usr/bin/env bash
[[ -n "${GBFC_LIB_DIR:-}" ]] || GBFC_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
[[ -f "$GBFC_LIB_DIR/common.sh" ]] && source "$GBFC_LIB_DIR/common.sh"


gbfc_stage_skills() {
  local stage
  stage="$(gbfc_stage_root)/antigravity-bestfriend"
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_STAGE_PLUGIN -> $stage"
    return 0
  fi
  rm -rf -- "$stage"
  mkdir -p -- "$stage/skills" "$stage/rules"
  gbfc_load_allowlist

  local name src dest overlay_file
  for name in "${GBFC_SKILL_NAMES[@]}"; do
    src="$GBFC_ROOT/vendor/skills/$name"
    [[ -d "$src" ]] || src="$GBFC_MANAGED/vendor/skills/$name"
    [[ -d "$src" ]] || gbfc_die "source skill missing: $src"
    dest="$stage/skills/$name"
    cp -a -- "$src" "$dest"

    overlay_file=""
    if [[ -f "$GBFC_ROOT/overlays/$name.prepend.md" ]]; then
      overlay_file="$GBFC_ROOT/overlays/$name.prepend.md"
    elif [[ -f "$GBFC_ROOT/overlays/$name.body.md" ]]; then
      overlay_file="$GBFC_ROOT/overlays/$name.body.md"
    elif [[ -f "$GBFC_MANAGED/overlays/$name.prepend.md" ]]; then
      overlay_file="$GBFC_MANAGED/overlays/$name.prepend.md"
    elif [[ -f "$GBFC_MANAGED/overlays/$name.body.md" ]]; then
      overlay_file="$GBFC_MANAGED/overlays/$name.body.md"
    fi

    python3 "$GBFC_ROOT/lib/overlay.py" --dest "$dest" --name "$name" ${overlay_file:+--prepend "$overlay_file"} \
      || gbfc_die "failed to apply overlay to skill $name"

    # Mark as owned
    cat << OWN_EOF > "$dest/$GBFC_MARKER"
{
  "product": "antigravity-bestfriend",
  "skill": "$name",
  "installedAt": "$(gbfc_now)"
}
OWN_EOF
  done

  # Copy rules into staged plugin
  cp -a -- "$GBFC_ROOT/rules/"*.md "$stage/rules/" 2>/dev/null || cp -a -- "$GBFC_MANAGED/rules/"*.md "$stage/rules/"

  # Render manifests & configs into staged plugin
  gbfc_render_template "$GBFC_ROOT/templates/plugin.template.json" "$stage/plugin.json"
  gbfc_render_template "$GBFC_ROOT/templates/mcp_config.template.json" "$stage/mcp_config.json"
  gbfc_render_template "$GBFC_ROOT/templates/hooks.template.json" "$stage/hooks.json"

  gbfc_info "Staged complete plugin in $stage"
}

gbfc_swap_skills() {
  local stage="$(gbfc_stage_root)/antigravity-bestfriend"

  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_INSTALL_PLUGIN -> agy plugin install $stage"
    return 0
  fi

  # Uninstall existing if present
  if agy plugin list 2>/dev/null | grep -q "antigravity-bestfriend"; then
    agy plugin uninstall "antigravity-bestfriend" 2>/dev/null || true
  fi

  # Install using native Antigravity lifecycle
  agy plugin install "$stage" || gbfc_die "agy plugin install failed for $stage"

  # Ensure it is enabled
  agy plugin enable "antigravity-bestfriend" 2>/dev/null || true

  # Also ensure managed runtime backup has skills & rules
  mkdir -p -- "$GBFC_MANAGED/skills" "$GBFC_MANAGED/rules"
  cp -a -- "$stage/skills/"* "$GBFC_MANAGED/skills/" 2>/dev/null || true
  cp -a -- "$stage/rules/"* "$GBFC_MANAGED/rules/" 2>/dev/null || true

  gbfc_info "Installed 40 skills via native Antigravity plugin lifecycle"
}

gbfc_install_router() {
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_INSTALL_ROUTER -> $GBFC_GLOBAL_ROUTER"
    return 0
  fi

  # Merge global router in ~/.gemini/GEMINI.md
  python3 - "$GBFC_GLOBAL_ROUTER" "$GBFC_ROOT/rules/AGENTS.md" <<'PY'
import sys
from pathlib import Path

target = Path(sys.argv[1])
source = Path(sys.argv[2])
block = source.read_text(encoding="utf-8").strip()

begin_marker = "<!-- ANTIGRAVITY-BESTFRIEND:BEGIN -->"
end_marker = "<!-- ANTIGRAVITY-BESTFRIEND:END -->"

existing = ""
if target.is_file():
    existing = target.read_text(encoding="utf-8")

if begin_marker in existing and end_marker in existing:
    pre = existing.split(begin_marker, 1)[0]
    post = existing.split(end_marker, 1)[1]
    new_content = pre.rstrip() + "\n\n" + block + "\n\n" + post.lstrip()
else:
    new_content = (existing.rstrip() + "\n\n" + block + "\n") if existing.strip() else (block + "\n")

target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(new_content, encoding="utf-8")
PY
  gbfc_info "Router merged into $GBFC_GLOBAL_ROUTER"
}
