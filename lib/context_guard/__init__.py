"""Context Guard: PREVENT > REDUCE > OFFLOAD > CIRCUIT BREAK > AUTOCOMPACT."""

PRODUCT = "antigravity-bestfriend"
HOOK_BIN_NAME = "agy-context-guard"
OWNED_EVENTS = (
    "PreToolUse",
    "PostToolUse",
    "PostToolBatch",
    "UserPromptSubmit",
    "PostCompact",
)
