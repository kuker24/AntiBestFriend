#!/usr/bin/env python3
"""Antigravity-native overlays for staged skills."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
DEFAULT_PATH_SKILLS = ("ask-matt", "grill-with-docs", "to-spec", "to-tickets")
SETUP_ANY_RE = re.compile(r"[^\n]*`/setup-matt-pocock-skills`[^\n]*\n?")

WHEN_TO_USE = {
    "ask-matt": (
        "Use when the user is choosing a workflow or asks which skill to run. "
        "Skip when the task is already a clear implement, review, design, or UI job."
    ),
    "grill-with-docs": (
        "Use when a feature still needs a plan, an interview, a glossary, or ADRs. "
        "Skip ordinary implementation, typo fixes, and architecture DAGs (those use Antigravity /plan mode)."
    ),
    "to-spec": (
        "Use after /grill-with-docs, or when the user asks to write a spec or run /to-spec. "
        "Do not interview. Skip ordinary implementation."
    ),
    "to-tickets": (
        "Use after a spec, or when the user asks to break work into tickets or run /to-tickets. "
        "Skip ordinary single-session implementation."
    ),
}


def overlay_marker(name: str) -> str:
    return f"<!-- antigravity-bestfriend-overlay:{name} -->"


def _render_fm_value(value: str) -> str:
    if any(ch in value for ch in ":#{}[]&*?|>!%@`") or " " in value:
        return json.dumps(value)
    return value


def upsert_frontmatter(text: str, updates: dict[str, str | None]) -> str:
    match = FRONTMATTER_RE.match(text)
    if not match:
        lines = ["---"]
        for key, value in updates.items():
            if value is None:
                continue
            lines.append(f"{key}: {_render_fm_value(value)}")
        lines.extend(["---", "", text])
        return "\n".join(lines)

    body = text[match.end() :]
    fm = match.group(1)
    for key, value in updates.items():
        pattern = re.compile(rf"^{re.escape(key)}\s*:.*$(?:\n[ \t].*)*", re.MULTILINE)
        if value is None:
            fm = pattern.sub("", fm, count=1)
            continue
        line = f"{key}: {_render_fm_value(value)}"
        if pattern.search(fm):
            fm = pattern.sub(line, fm, count=1)
        else:
            fm = fm.rstrip() + f"\n{line}\n"
    fm = re.sub(r"\n{3,}", "\n\n", fm).strip("\n") + "\n"
    return f"---\n{fm}---\n{body}"


def split_frontmatter(text: str) -> tuple[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return "", text
    return text[: match.end()], text[match.end() :]


def prepend_after_frontmatter(text: str, extra: str) -> str:
    extra = extra.lstrip("\n")
    if extra in text:
        return text
    match = FRONTMATTER_RE.match(text)
    if not match:
        return extra + text
    return text[: match.end()] + extra + text[match.end() :]


def ensure_overlay_body(text: str, name: str, extra: str) -> str:
    extra = extra.lstrip("\n")
    if not extra.endswith("\n"):
        extra += "\n"
    marker = overlay_marker(name)
    if marker not in extra:
        extra = f"{marker}\n\n{extra}"
    return prepend_after_frontmatter(text, extra)


def replace_all(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def rewrite_impeccable_paths(dest: Path) -> None:
    replacements = [
        ("node .grok/skills/impeccable/scripts/", "node <skill-base-dir>/scripts/"),
        (".grok/skills/impeccable/scripts", "~/.gemini/antigravity-cli/plugins/antigravity-bestfriend/skills/impeccable/scripts"),
        ("Bash(node .grok/skills/impeccable/scripts/*)", "run_command(node *impeccable/scripts/*)"),
        ("Bash(python3 *design-intelligence.py", "run_command(python3 *design-intelligence.py"),
        ("<skill-base-dir>/scripts/design-intelligence.py", "$HOME/.gemini/antigravity-bestfriend/scripts/design-intelligence.py"),
        ("$HOME/.grok/skills/impeccable", "$HOME/.gemini/antigravity-cli/plugins/antigravity-bestfriend/skills/impeccable"),
        ("~/.grok/skills/impeccable", "~/.gemini/antigravity-cli/plugins/antigravity-bestfriend/skills/impeccable"),
        ("$HOME/.claude/skills/impeccable", "$HOME/.gemini/antigravity-cli/plugins/antigravity-bestfriend/skills/impeccable"),
        ("~/.claude/skills/impeccable", "~/.gemini/antigravity-cli/plugins/antigravity-bestfriend/skills/impeccable"),
    ]
    for path in dest.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".md", ".mjs", ".js", ".py", ".json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        new = replace_all(text, replacements)
        if new != text:
            path.write_text(new, encoding="utf-8")


def rewrite_found_this_design_bank(dest: Path) -> None:
    lib = dest / "scripts" / "lib.mjs"
    if not lib.is_file():
        return
    body = lib.read_text(encoding="utf-8")
    header = '''import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

function catalogsOk(root) {
  return (
    !!root &&
    fs.existsSync(path.join(root, "Refero/bank/catalog.json")) &&
    fs.existsSync(path.join(root, "motionsites/library/catalog.json"))
  );
}

function bankFromAdapterConfig() {
  const cfg = path.join(os.homedir(), ".gemini/antigravity-bestfriend/config/design-bank.json");
  try {
    const data = JSON.parse(fs.readFileSync(cfg, "utf8"));
    if (data && typeof data.root === "string" && catalogsOk(data.root)) return data.root;
  } catch {
    /* doctor reports NOT_CONFIGURED; do not invent a path */
  }
  return "";
}

export const DEFAULT_BANK =
  process.env.ANTIGRAVITY_DESIGN_BANK ||
  process.env.GROK_DESIGN_BANK ||
  process.env.CLAUDE_DESIGN_BANK ||
  bankFromAdapterConfig() ||
  path.join(os.homedir(), "Downloads/LAB GITHUB/Design") ||
  path.join(os.homedir(), "Design");

export function resolveBankRoot(explicit) {
  const candidates = [
    explicit,
    process.env.ANTIGRAVITY_DESIGN_BANK,
    process.env.GROK_DESIGN_BANK,
    process.env.CLAUDE_DESIGN_BANK,
    bankFromAdapterConfig(),
    path.join(os.homedir(), "Downloads/LAB GITHUB/Design"),
    path.join(os.homedir(), "Design"),
  ].filter(Boolean);
  for (const root of candidates) {
    if (catalogsOk(root)) return root;
  }
  return explicit || process.env.ANTIGRAVITY_DESIGN_BANK || DEFAULT_BANK;
}

'''
    marker = "export const REFERO_KINDS"
    if marker not in body:
        cleaned = re.sub(
            r"export function resolveBankRoot\([^)]*\) \{[\s\S]*?\n\}\n*",
            "",
            body,
            count=1,
        )
        lib.write_text(header + cleaned, encoding="utf-8")
    else:
        rest = body.split(marker, 1)[1]
        rest = re.sub(
            r"\nexport function resolveBankRoot\([^)]*\) \{[\s\S]*?\n\}\n*",
            "\n",
            rest,
            count=1,
        )
        lib.write_text(header + marker + rest, encoding="utf-8")

    # Fix space-in-path issue in search.mjs
    search_mjs = dest / "scripts" / "search.mjs"
    if search_mjs.is_file():
        s_body = search_mjs.read_text(encoding="utf-8")
        s_fixed = re.sub(
            r"const isMain\s*=\s*import\.meta\.url\s*===[^;]+;",
            'import { fileURLToPath } from "node:url";\nconst isMain = process.argv[1] ? fileURLToPath(import.meta.url) === path.resolve(process.argv[1]) : false;',
            s_body,
        )
        if s_fixed != s_body:
            search_mjs.write_text(s_fixed, encoding="utf-8")


def apply_skill(dest: Path, name: str, prepend: str | None) -> None:
    skill = dest / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    updates: dict[str, str | None] = {"name": name}
    extras: list[tuple[str, str]] = []

    if name in DEFAULT_PATH_SKILLS:
        updates["disable-model-invocation"] = None
        updates["when-to-use"] = WHEN_TO_USE[name]

    if name == "matt-implement":
        extras = [
            ("use /code-review", "use /matt-code-review"),
            (
                "Default Grok write path is bundled /implement; this skill is the Matt ticket loop only.",
                "Default Antigravity write path is this session; this skill is the Matt ticket loop only.",
            ),
            ("bundled /implement", "in-session write"),
            ("Default Claude write path is this session", "Default Antigravity write path is this session"),
        ]
    elif name == "tdd":
        extras = [
            (
                "see bundled `/review`, or `/matt-code-review` for the two-axis Matt review",
                "see in-session review, or `/matt-code-review` for the two-axis Matt review",
            ),
            ("bundled `/review`", "in-session review"),
        ]
    elif name == "browser-act":
        extras = [
            ("allowed-tools: run_terminal_command", "allowed-tools: run_command"),
            ("allowed-tools: Bash", "allowed-tools: run_command"),
            (
                "NEVER run browser-act commands until this skill is loaded. Use run_terminal_command, not a raw unguided bash one-liner",
                "NEVER run browser-act commands until this skill is loaded. Use run_command, not a raw unguided one-liner",
            ),
            ("via `run_terminal_command`", "via run_command"),
            ("Use run_terminal_command", "Use run_command"),
            ("via Bash", "via run_command"),
            ("Use Bash", "Use run_command"),
        ]
    elif name == "adhd":
        updates["when-to-use"] = (
            "Use only for difficult divergent decisions, fuzzy debugging, API/schema alternatives, or trap detection. Skip ordinary CRUD, typos, and bugs with a known cause."
        )
        extras = [
            ("Spawn 5 **parallel** `spawn_subagent` calls", "Spawn 5 **parallel** invoke_subagent calls"),
            ("Grok `spawn_subagent` gives each branch a fresh context.", "The invoke_subagent tool gives each branch a fresh context."),
            ("inside GrokBuild with no extra install required.", "inside Antigravity CLI with no extra install required."),
            ("inside Claude Code with no extra install required.", "inside Antigravity CLI with no extra install required."),
            ("Agent/Task", "invoke_subagent"),
        ]
    elif name == "emil-design-eng":
        updates["description"] = (
            "UI motion, transition, and interaction feel after Impeccable. Use when polishing animation, easing, press/hover, or interruptible chrome motion. Do not use for static UI, photoreal video, or scroll-world camera chains."
        )
        updates["when-to-use"] = (
            "Use only for motion, transition, or interaction work after Impeccable. Do not use for static UI or backend-only work."
        )
    elif name == "full-audit-keamanan":
        updates["when-to-use"] = (
            "Use on demand for auth, secrets, APIs, payment, upload, webhook, or privileged-operation risk. Do not use for ordinary product UI."
        )
    elif name == "full-performance-audit":
        updates["when-to-use"] = (
            "Use on demand for measured regressions in bundle, query, memory, latency, or Core Web Vitals (LCP, INP, CLS)."
        )
    elif name == "chrome-devtools-axi":
        updates["description"] = (
            "Control a Chromium session through chrome-devtools-axi after agy-chromium-cdp start. Use when an observed browser issue needs diagnostics (click, form, console, network). Skip if curl or read_url_content is enough. Not for exploratory multi-role QA (use browser-act)."
        )
        updates["when-to-use"] = (
            "Use when an observed browser issue needs Chromium diagnostics. Start agy-chromium-cdp first and attach via CHROME_DEVTOOLS_AXI_BROWSER_URL. Skip if curl or read_url_content is enough."
        )
        extras = [
            ("grok-chromium-cdp", "agy-chromium-cdp"),
            ("claude-chromium-cdp", "agy-chromium-cdp"),
            ("$HOME/.grok/bin/grok-chromium-cdp", "$HOME/.gemini/antigravity-bestfriend/bin/agy-chromium-cdp"),
            ("~/.grok/bin/grok-chromium-cdp", "~/.gemini/antigravity-bestfriend/bin/agy-chromium-cdp"),
            ("$HOME/.claude/grokbestfriend-claude/bin/claude-chromium-cdp", "$HOME/.gemini/antigravity-bestfriend/bin/agy-chromium-cdp"),
            ("~/.claude/grokbestfriend-claude/bin/claude-chromium-cdp", "~/.gemini/antigravity-bestfriend/bin/agy-chromium-cdp"),
            ("http://127.0.0.1:9222", "http://127.0.0.1:9223"),
        ]
    elif name == "matt-code-review":
        updates["description"] = (
            "Two-axis Standards + Spec review of a pinned diff. Use only when the user asks for that two-axis review, or runs /matt-code-review. Default review is in-session."
        )
        extras = [
            ("bundled /review", "in-session review"),
            ("spawn_subagent", "invoke_subagent"),
            ("Agent", "invoke_subagent"),
        ]
        text = SETUP_ANY_RE.sub("", text)
        text = text.replace("run `/setup-matt-pocock-skills` if not.", "")
        text = text.replace("run `/setup-matt-pocock-skills` if `docs/agents/issue-tracker.md` is missing.", "use the local tracker default if `docs/agents/issue-tracker.md` is missing.")
    elif name == "gh-axi":
        updates["when-to-use"] = (
            "Use for GitHub issues, PRs, Actions, and releases via npx -y gh-axi. Ask the human to run gh auth login if gh is not authenticated."
        )
    elif name in ("visual-studio", "scroll-world", "found-this-design"):
        extras = [
            ("bundled `imagine`", "Antigravity native generate_image tool"),
            ("bundled imagine", "Antigravity native generate_image tool"),
            ("GrokBuild image_gen", "Antigravity native generate_image tool"),
            ("GrokBuild image/video tools", "Antigravity native generate_image tool"),
            ("Claude-native image tools", "Antigravity native generate_image tool"),
            ("Claude-native image generation", "Antigravity native generate_image tool"),
            ("Use only GrokBuild image/video tools. Do not call an external", "Use Antigravity native generate_image tool. Do not call an untrusted external"),
            ("Load bundled imagine before any generate/edit/video call.", "Use Antigravity native generate_image tool."),
            ("Before any `image_gen`, `image_edit`, `image_to_video`, or", "Before any image or video generation,"),
            ("`reference_to_video` call, load bundled `imagine`. Tool choice, prompt", "use generate_image. Prompt"),
        ]
    elif name in ("to-spec", "to-tickets"):
        text = SETUP_ANY_RE.sub("", text)
        text = text.replace("run `/setup-matt-pocock-skills` if not.", "")

    # Universal path and residue replacements
    extras.extend([
        ("~/.claude/grokbestfriend-claude/config/model-pool.json", "~/.gemini/antigravity-bestfriend/config/model-pool.json"),
        ("$HOME/.claude/grokbestfriend-claude/config/model-pool.json", "$HOME/.gemini/antigravity-bestfriend/config/model-pool.json"),
        ("~/.claude/grokbestfriend-claude/rules/", "~/.gemini/antigravity-bestfriend/rules/"),
        ("$HOME/.claude/grokbestfriend-claude/rules/", "$HOME/.gemini/antigravity-bestfriend/rules/"),
        ("~/.claude/grokbestfriend-claude/", "~/.gemini/antigravity-bestfriend/"),
        ("$HOME/.claude/grokbestfriend-claude/", "$HOME/.gemini/antigravity-bestfriend/"),
        ("~/.claude/skills/", "~/.gemini/config/plugins/antigravity-bestfriend/skills/"),
        ("$HOME/.claude/skills/", "$HOME/.gemini/config/plugins/antigravity-bestfriend/skills/"),
        ("grokbestfriend-claude", "antigravity-bestfriend"),
        ("claude-gbf", "agy-bestfriend"),
        ("grok-chromium-cdp", "agy-chromium-cdp"),
        ("claude-chromium-cdp", "agy-chromium-cdp"),
        ("Bash", "run_command"),
        ("Read", "view_file"),
        ("Edit", "replace_file_content"),
        ("Write", "write_to_file"),
    ])

    text = upsert_frontmatter(text, updates)
    if prepend:
        text = ensure_overlay_body(text, name, prepend)
    if extras:
        text = replace_all(text, extras)
    skill.write_text(text, encoding="utf-8")

    if name == "found-this-design":
        rewrite_found_this_design_bank(dest)
    if name == "impeccable":
        rewrite_impeccable_paths(dest)
    for path in dest.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".mjs", ".js", ".py", ".json"}:
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        new = replace_all(
            body,
            [
                ("~/.claude/grokbestfriend-claude/rules/", "~/.gemini/antigravity-bestfriend/rules/"),
                ("$HOME/.claude/grokbestfriend-claude/rules/", "$HOME/.gemini/antigravity-bestfriend/rules/"),
                ("~/.claude/grokbestfriend-claude/", "~/.gemini/antigravity-bestfriend/"),
                ("$HOME/.claude/grokbestfriend-claude/", "$HOME/.gemini/antigravity-bestfriend/"),
                ("~/.claude/skills/", "~/.gemini/config/plugins/antigravity-bestfriend/skills/"),
                ("$HOME/.claude/skills/", "$HOME/.gemini/config/plugins/antigravity-bestfriend/skills/"),
                ("~/.claude/projects/", "~/.gemini/antigravity-bestfriend/projects/"),
                ("$HOME/.claude/projects/", "$HOME/.gemini/antigravity-bestfriend/projects/"),
                ("~/.cursor/projects/", "~/.gemini/antigravity-bestfriend/projects/"),
                ("grokbestfriend-claude", "antigravity-bestfriend"),
                ("model-pool.json", "model-pool.json"),
                ("grok-chromium-cdp", "agy-chromium-cdp"),
                ("claude-chromium-cdp", "agy-chromium-cdp"),
                ("$HOME/.grok/bin/claude-chromium-cdp", "$HOME/.gemini/antigravity-bestfriend/bin/agy-chromium-cdp"),
                ("~/.grok/bin/claude-chromium-cdp", "~/.gemini/antigravity-bestfriend/bin/agy-chromium-cdp"),
                ("$HOME/.claude/grokbestfriend-claude/bin/claude-chromium-cdp", "$HOME/.gemini/antigravity-bestfriend/bin/agy-chromium-cdp"),
                ("~/.claude/grokbestfriend-claude/bin/claude-chromium-cdp", "~/.gemini/antigravity-bestfriend/bin/agy-chromium-cdp"),
            ],
        )
        if name == "chrome-devtools-axi":
            new = new.replace("http://127.0.0.1:9222", "http://127.0.0.1:9223")
        if new != body:
            path.write_text(new, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--prepend", default="")
    args = parser.parse_args()
    prepend = Path(args.prepend).read_text(encoding="utf-8") if args.prepend else None
    apply_skill(Path(args.dest), args.name, prepend)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
