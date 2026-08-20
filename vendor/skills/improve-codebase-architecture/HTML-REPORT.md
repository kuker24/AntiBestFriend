# HTML Report Format

The architectural review is a single self-contained HTML file in the OS temp directory.

**Default is zero-network.** Inline CSS and HTML/SVG only. Do not load Tailwind, Mermaid, fonts, or any other CDN. Mermaid/CDN is an optional enhancement only if the user explicitly asked and the environment already has it.

Hand-built divs and inline SVG handle graph-shaped diagrams (call graphs, dependencies, sequences) and editorial visuals (mass diagrams, cross-sections).

## Scaffold (default, zero-network)

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Architecture review — {{repo name}}</title>
    <style>
      :root { color-scheme: light; }
      body { margin: 0; background: #fafaf9; color: #0f172a; font: 16px/1.45 system-ui, sans-serif; }
      main { max-width: 64rem; margin: 0 auto; padding: 3rem 1.5rem; }
      article { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem; margin: 1.5rem 0; }
      .files { font-family: ui-monospace, monospace; font-size: 0.875rem; }
      .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.75rem; }
      .strong { background: #d1fae5; color: #065f46; }
      .explore { background: #fef3c7; color: #92400e; }
      .speculative { background: #e2e8f0; color: #334155; }
      .diagram { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; min-height: 12rem; }
      .box { border: 2px solid #0f172a; padding: 0.5rem; background: #fff; }
      .deep { background: linear-gradient(135deg, #0f172a, #1e293b); color: #f8fafc; }
      .leak { stroke: #dc2626; }
      .seam { stroke-dasharray: 4 4; }
    </style>
  </head>
  <body>
    <main>
      <header>...</header>
      <section id="candidates">...</section>
      <section id="top-recommendation">...</section>
    </main>
  </body>
</html>
```

Do not add `<script src="https://...">` or ESM imports from a CDN in the default report.

## Header

Repo name, date, and a compact legend: solid box = module, dashed line = seam, red arrow = leakage, thick dark box = deep module. No introduction paragraph — straight into the candidates.

## Candidate card

The diagrams carry the weight. Prose is sparse, plain, and uses the glossary terms from the codebase-design vocabulary without ceremony.

Each candidate is one `<article>`:

- **Title** — short, names the deepening (e.g. "Collapse the Order intake pipeline").
- **Badge row** — recommendation strength (`Strong` = emerald, `Worth exploring` = amber, `Speculative` = slate), plus a tag for the dependency category (`in-process`, `local-substitutable`, `ports & adapters`, `mock`).
- **Files** — monospaced list.
- **Before / After diagram** — the centrepiece. Two columns, side by side. See patterns below.
- **Problem** — one sentence. What hurts.
- **Solution** — one sentence. What changes.
- **Wins** — bullets, ≤6 words each. e.g. "Tests hit one interface", "Pricing logic stops leaking", "Delete 4 shallow wrappers".
- **ADR callout** (if applicable) — one line in an amber-tinted box.

No paragraphs of explanation. If the diagram needs a paragraph to be understood, redraw the diagram.

## Diagram patterns

Pick the pattern that fits the candidate. Mix them. Don't make every diagram look the same.

### Inline SVG / boxes (default)

Modules as `<div>`s with borders and labels. Arrows as inline SVG `<line>` or `<path>` elements. Reach for this for call flow, leakage, and the "after" thick-bordered deep module.

### Cross-section (good for layered shallowness)

Stack horizontal bands to show layers a call passes through. Before: 6 thin layers each doing nothing. After: 1 thick band labelled with the consolidated responsibility.

### Mass diagram (good for "interface as wide as implementation")

Two rectangles per module — one for interface surface area, one for implementation. Before: interface rectangle is nearly as tall as the implementation rectangle (shallow). After: interface rectangle is short, implementation rectangle is tall (deep).

### Call-graph collapse

Before: a tree of function calls rendered as nested boxes. After: the same tree collapsed into one box, with the now-internal calls shown faded inside it.

### Optional Mermaid (enhancement only)

Only if the user explicitly asked and a local/offline Mermaid is already available. Never the default. Never a CDN in the default report.

## Style guidance

- Lean editorial, not corporate-dashboard. Generous whitespace.
- Colour sparingly: one accent plus red for leakage and amber for warnings.
- Keep diagrams ~320px tall so before/after sits comfortably side by side.
- The default report has no scripts.

## Top recommendation section

One larger card. Candidate name, one sentence on why, anchor link to its card. That's it.

## Tone

Plain English, concise — but the architectural nouns and verbs come from the codebase-design vocabulary.

**Use exactly:** module, interface, implementation, depth, deep, shallow, seam, adapter, leverage, locality.

**Never substitute:** component, service, unit (for module) · API, signature (for interface) · boundary (for seam) · layer, wrapper (for module, when you mean module).
