"""Context Guard: PREVENT > REDUCE > OFFLOAD > CIRCUIT BREAK > AUTOCOMPACT."""

PRODUCT = "grokbestfriend-claude"
HOOK_BIN_NAME = "gbfc-context-guard"
OWNED_EVENTS = (
    "PreToolUse",
    "PostToolUse",
    "PostToolBatch",
    "UserPromptSubmit",
    "PostCompact",
)
