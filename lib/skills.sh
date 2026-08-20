#!/usr/bin/env bash

gbfc_stage_skills() {
  local stage
  stage="$(gbfc_stage_root)/skills"
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_STAGE_SKILLS -> $stage"
    return 0
  fi
  rm -rf -- "$stage"
  mkdir -p -- "$stage"
  gbfc_load_allowlist

  local name src dest overlay_file
  for name in "${GBFC_SKILL_NAMES[@]}"; do
    src="$GBFC_VENDOR_SOURCE/vendor/skills/$name"
    [[ -d "$src" ]] || gbfc_die "source skill missing: $src"
    dest="$stage/$name"
    cp -a -- "$src" "$dest"

    overlay_file=""
    if [[ -f "$GBFC_ROOT/overlays/$name.prepend.md" ]]; then
      overlay_file="$GBFC_ROOT/overlays/$name.prepend.md"
    elif [[ -f "$GBFC_ROOT/overlays/$name.body.md" ]]; then
      overlay_file="$GBFC_ROOT/overlays/$name.body.md"
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
  gbfc_info "Staged ${#GBFC_SKILL_NAMES[@]} skills in $stage"
}

gbfc_swap_skills() {
  local stage="$(gbfc_stage_root)/skills"
  local target_plugin="$GBFC_PLUGIN_DIR/skills"
  local target_managed="$GBFC_MANAGED/skills"

  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_SWAP_SKILLS -> $target_plugin"
    return 0
  fi

  mkdir -p -- "$target_plugin" "$target_managed"
  gbfc_load_allowlist

  local name
  for name in "${GBFC_SKILL_NAMES[@]}"; do
    rm -rf -- "$target_plugin/$name" "$target_managed/$name"
    cp -a -- "$stage/$name" "$target_plugin/$name"
    cp -a -- "$stage/$name" "$target_managed/$name"
  done
  gbfc_info "Installed ${#GBFC_SKILL_NAMES[@]} skills into $target_plugin"
}

gbfc_install_router() {
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_INSTALL_ROUTER -> $GBFC_PLUGIN_DIR/rules and $GBFC_GLOBAL_ROUTER"
    return 0
  fi

  mkdir -p -- "$GBFC_PLUGIN_DIR/rules" "$GBFC_MANAGED/rules"
  cp -a -- "$GBFC_ROOT/rules/"*.md "$GBFC_PLUGIN_DIR/rules/"
  cp -a -- "$GBFC_ROOT/rules/"*.md "$GBFC_MANAGED/rules/"

  # Install manifest & config in plugin
  cp -a -- "$GBFC_ROOT/plugin.json" "$GBFC_PLUGIN_DIR/plugin.json"
  cp -a -- "$GBFC_ROOT/mcp_config.json" "$GBFC_PLUGIN_DIR/mcp_config.json"
  cp -a -- "$GBFC_ROOT/hooks.json" "$GBFC_PLUGIN_DIR/hooks.json"

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
  gbfc_info "Router installed in $GBFC_PLUGIN_DIR and merged into $GBFC_GLOBAL_ROUTER"
}
