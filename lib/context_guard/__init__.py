"""Context Guard: image budgeting hook for Antigravity CLI (PreToolUse)."""

PRODUCT = "antigravity-bestfriend"
HOOK_BIN_NAME = "agy-context-guard"
OWNED_EVENTS = (
    "PreToolUse",
)
