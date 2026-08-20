#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import {
  MOTION_JENIS,
  argValue,
  extractHexes,
  tokenize,
} from "./lib.mjs";

const KIND_ALIASES = [
  { re: /\b(dark|gelap|midnight|noir)\b/i, kinds: ["dark-mode"], theme: "dark" },
  { re: /\b(light|terang|cream|paper|ivory)\b/i, kinds: [], theme: "light" },
  { re: /\b(editorial|magazine|newspaper|serif)\b/i, kinds: ["editorial"] },
  { re: /\b(playful|fun|colorful|cartoon)\b/i, kinds: ["playful"] },
  { re: /\b(mono|monochrome|grayscale|greyscale)\b/i, kinds: ["monochrome"] },
  { re: /\b(high[-\s]?contrast|swiss engineering)\b/i, kinds: ["high-contrast"] },
  { re: /\b(gradient|aurora|glow|soft)\b/i, kinds: ["soft-gradients"] },
  { re: /\b(brutalist|raw|concrete)\b/i, kinds: ["brutalist"] },
  { re: /\b(minimal|clean|swiss|quiet)\b/i, kinds: ["minimal"] },
];

const SURFACE_ALIASES = [
  { re: /\b(dashboard|admin|settings|operate)\b/i, surface: "dashboard" },
  { re: /\b(landing|homepage|marketing|home page)\b/i, surface: "landing-page" },
  { re: /\bhero\b/i, surface: "hero" },
  { re: /\b(about|tentang)\b/i, surface: "about" },
  { re: /\b(pricing|harga)\b/i, surface: "pricing" },
  { re: /\bfooter\b/i, surface: "footer" },
  { re: /\b(404|not found)\b/i, surface: "404" },
  { re: /\b(mobile|app screen)\b/i, surface: "mobile-app" },
  { re: /\b(feature|benefits)\b/i, surface: "features" },
  { re: /\b(blog|article|docs)\b/i, surface: "blog" },
  { re: /\b(testimonial|review)\b/i, surface: "testimonials" },
  { re: /\b(stats|metrics)\b/i, surface: "stats" },
  { re: /\b(cta|waitlist)\b/i, surface: "cta" },
  { re: /\b(3d|webgl)\b/i, surface: "3d-website" },
  { re: /\b(portfolio|gallery|showcase)\b/i, surface: "portfolio" },
];

const INDUSTRY_ALIASES = [
  { re: /\b(saas|software|b2b|productivity)\b/i, industry: "saas" },
  { re: /\b(wellness|health|healthcare|medical)\b/i, industry: "wellness" },
  { re: /\b(portfolio|personal)\b/i, industry: "portfolio" },
  { re: /\b(agency|studio)\b/i, industry: "agency" },
  { re: /\b(finance|fintech|bank)\b/i, industry: "finance" },
  { re: /\b(shop|store|ecommerce|e-commerce)\b/i, industry: "commerce" },
];

function readIf(file) {
  try {
    return fs.readFileSync(file, "utf8");
  } catch {
    return "";
  }
}

function productNameFrom(productMd, pkg) {
  const heading = productMd.match(/^#\s+(.+)$/m);
  if (heading) {
    const name = heading[1].replace(/^Product\b[:\s]*/i, "").trim();
    if (name && name.toLowerCase() !== "product") return name;
  }
  const purpose = productMd.match(/##\s+Product Purpose\s+([\s\S]*?)(?:\n##\s|$)/i);
  if (purpose) {
    const first = purpose[1].trim().split(/\n/)[0];
    if (first && first.length < 80) return first.replace(/^\[|\]$/g, "");
  }
  if (pkg?.name && pkg.name !== "package") return pkg.name;
  return "";
}

function detectTheme(blob, kinds) {
  if (kinds.includes("dark-mode")) return "dark";
  for (const rule of KIND_ALIASES) {
    if (rule.theme && rule.re.test(blob)) return rule.theme;
  }
  const hexes = extractHexes(blob).slice(0, 12);
  if (!hexes.length) return "unknown";
  let dark = 0;
  let light = 0;
  for (const hex of hexes) {
    const hsl = hex.replace("#", "");
    const r = parseInt(hsl.slice(0, 2), 16);
    const g = parseInt(hsl.slice(2, 4), 16);
    const b = parseInt(hsl.slice(4, 6), 16);
    const l = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
    if (l < 0.35) dark += 1;
    else if (l > 0.65) light += 1;
  }
  if (dark > light + 1) return "dark";
  if (light > dark + 1) return "light";
  return "unknown";
}

function firstMatch(rules, blob, key) {
  for (const rule of rules) {
    if (rule.re.test(blob)) return rule[key];
  }
  return "";
}

function detectKinds(blob) {
  const kinds = [];
  for (const rule of KIND_ALIASES) {
    if (!rule.kinds.length) continue;
    if (rule.re.test(blob)) {
      for (const k of rule.kinds) if (!kinds.includes(k)) kinds.push(k);
    }
  }
  return kinds;
}

function detectMode(surface, blob) {
  if (/\b(docs|article|blog|help|changelog)\b/i.test(blob) || surface === "blog") {
    return "Read";
  }
  if (
    /\b(dashboard|admin|settings|editor|tool)\b/i.test(blob) ||
    surface === "dashboard"
  ) {
    return "Operate";
  }
  if (
    /\b(portfolio|gallery|showcase)\b/i.test(blob) ||
    surface === "portfolio"
  ) {
    return "Experience";
  }
  return "Persuade";
}

function detectIntent(blob, hasDesign) {
  if (/\b(redesign|rebrand|ganti desain|design ulang|desain ulang)\b/i.test(blob)) {
    return "redesign";
  }
  if (
    /\b(section|seksi|bagian|hero|footer|cta|pricing)\b/i.test(blob) &&
    !/\b(whole|keseluruhan|seluruh|full (site|page)|identitas)\b/i.test(blob)
  ) {
    return "section";
  }
  if (hasDesign) return "redesign";
  return "new";
}

const WHOLE_SURFACES = new Set([
  "landing-page",
  "hero",
  "mobile-app",
  "3d-website",
  "portfolio",
]);

function laneHint(intent, surface) {
  if (surface === "dashboard") return "identity";
  if ((intent === "redesign" || intent === "new") && WHOLE_SURFACES.has(surface)) {
    return "both";
  }
  if (MOTION_JENIS.includes(surface)) return "section";
  if (intent === "section") return "section";
  if (intent === "redesign" || intent === "new") return "identity";
  return "both";
}

function compactQuery({ query, productName, industry, kinds, surface, extra }) {
  const parts = [query, productName, industry, ...kinds, surface, extra]
    .filter(Boolean)
    .join(" ");
  return tokenize(parts).slice(0, 24).join(" ");
}

function parsePkg(text) {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export function fingerprint({ cwd, query = "", count = 3, intent: intentArg }) {
  const root = path.resolve(cwd || process.cwd());
  const productMd = readIf(path.join(root, "PRODUCT.md"));
  const designMd = readIf(path.join(root, "DESIGN.md"));
  const pkg = parsePkg(readIf(path.join(root, "package.json")));
  const wantBlob = [query, productMd, pkg?.name, pkg?.description]
    .filter(Boolean)
    .join("\n");
  const blob = [wantBlob, designMd].filter(Boolean).join("\n");

  const fromQuery = detectKinds(query);
  const kinds = fromQuery.length ? fromQuery : detectKinds(wantBlob);
  const surface = firstMatch(SURFACE_ALIASES, wantBlob, "surface") || "landing-page";
  const industry = firstMatch(INDUSTRY_ALIASES, wantBlob, "industry");
  const theme = detectTheme(`${query}\n${designMd}`, kinds);
  const intent = intentArg || detectIntent(blob, Boolean(designMd));
  const productName = productNameFrom(productMd, pkg);
  const hexes = extractHexes(designMd).slice(0, 16);
  const n = Number(count) === 5 ? 5 : 3;

  const brief = {
    intent,
    mode: detectMode(surface, blob),
    surface,
    industry,
    theme,
    kinds,
    query: compactQuery({
      query,
      productName,
      industry,
      kinds,
      surface,
      extra: [pkg?.description, productMd]
        .filter(Boolean)
        .join(" ")
        .slice(0, 400),
    }),
    hexes,
    productName,
    count: n,
    laneHint: laneHint(intent, surface),
    avoid: [],
    sources: {
      product: Boolean(productMd),
      design: Boolean(designMd),
      package: Boolean(pkg),
    },
  };
  return brief;
}

const isMain =
  import.meta.url === `file://${path.resolve(process.argv[1] || "")}`;

if (isMain) {
  const argv = process.argv.slice(2);
  const countRaw = argValue(argv, "count", "3");
  const brief = fingerprint({
    cwd: argValue(argv, "cwd", process.cwd()),
    query: argValue(argv, "query", ""),
    count: countRaw,
    intent: argValue(argv, "intent", ""),
  });
  process.stdout.write(`${JSON.stringify(brief, null, 2)}\n`);
}
