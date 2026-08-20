# UI resource hub

Load this after the visual world is settled and before installing a catalog component. Impeccable remains the art director. MCP `shadcn` is the only UI registry server.

## Gate

- `components.json` in cwd: search the hub.
- React + Tailwind, no `components.json`: offer `npx shadcn@<pinned> init`. Do not run it silently.
- GrokBestFriend itself, backend, Python, or a non-UI tree: do not init and do not call the hub.
- Context7 is documentation. Web search is not an installer.

## Loop

1. Search. Do not install on the first hit. Public-namespace search can add the registry to `components.json`; inspect that git diff and do not keep unused registries.
2. Inspect 1–3 candidates: registry namespace, dependencies, file targets, and files that already exist in the project.
3. Pick one that fits the committed world and the surface hierarchy.
4. If the candidate would overwrite an existing project file, reject it or require explicit approval. Do not assume third-party items belong in `components/ui`.
5. Install once. Restyle to project tokens. Load `/emil-design-eng` only if motion still needs a pass.

## Namespace

| Need | Registry |
| --- | --- |
| Form, dialog, table, chart, Lucide icon | `@shadcn` |
| Animation primitive, animated icon | `@animate-ui` |
| Fancy visual, background, 3D | `@aceternity` or `@react-bits` |
| Hero, marquee, landing effect | `@magicui`, `@aceternity`, or `@react-bits` |
| Gantt, dropzone, complex SaaS control | `@kibo-ui` |

Do not add Magic UI MCP, Kibo MCP, 21st.dev, or community React Bits / Aceternity servers.

## Restraint

Decorative components only when they clarify hierarchy, interaction, brand, or data. One authored landing moment — not aurora plus particles plus marquee plus glow plus 3D plus confetti.

Dashboards (Operate) may be denser: KPI cards, Lucide icons, sparkline, bar/line/area/donut/radial/radar (shadcn/Recharts), table, badge, progress, empty state, avatar, tooltip, one micro-interaction. Still one system, not six libraries in one viewport.
