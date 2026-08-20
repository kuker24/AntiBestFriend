# Specialist status

162 skill folders are not 162 capabilities. About 85 are catalogue stubs
that advertise an upstream install.

ZIP rows are never activated. `vendor/skill-allowlist.txt` is the
availability evidence for GrokBestFriend skills.

| Catalog name | ZIP folder | execution_class |
|---|---|---|
| design-taste-frontend | taste-skill | reference-only |
| gpt-taste | gpt-tasteskill | reference-only |
| design-brief | design-brief | reference-only |
| reference-design-contract | reference-design-contract | reference-only |
| creative-director | creative-director | stub |
| brand-extract | brand-extract | connector-required |
| emil-design-eng | emil-design-eng | reference-only |
| review-animations | review-animations | reference-only + DISABLE_MODEL_INVOCATION |
| d3-visualization, threejs, shader-dev, apple-hig, platform-design, shadcn-ui, figma-* | same | stub |

At probe time, ZIP `emil-design-eng` may report
`available_via = gbf-skill:emil-design-eng` if that name is allowlisted.
That hint is not a second owner and is not stored in the catalog.

The ZIP `shadcn-ui` stub is not the pinned shadcn MCP.
