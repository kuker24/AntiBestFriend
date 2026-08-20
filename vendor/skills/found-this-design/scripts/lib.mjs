import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const DEFAULT_BANK =
  process.env.GROK_DESIGN_BANK || path.join(os.homedir(), "Design");

export const REFERO_KINDS = [
  "dark-mode",
  "editorial",
  "playful",
  "monochrome",
  "high-contrast",
  "soft-gradients",
  "brutalist",
  "minimal",
  "lainnya",
];

export const MOTION_JENIS = [
  "hero",
  "landing-page",
  "features",
  "about",
  "footer",
  "cta",
  "pricing",
  "404",
  "mobile-app",
  "testimonials",
  "stats",
  "blog",
  "carousel",
  "3d-website",
];

const STOP = new Set([
  "the",
  "a",
  "an",
  "and",
  "or",
  "of",
  "for",
  "to",
  "in",
  "on",
  "with",
  "from",
  "this",
  "that",
  "its",
  "into",
  "over",
  "under",
  "your",
  "our",
  "web",
  "website",
  "page",
  "app",
  "site",
  "design",
  "desain",
  "dari",
  "yang",
  "untuk",
  "dan",
  "atau",
  "ini",
  "itu",
  "dengan",
  "pada",
  "sebuah",
  "sebagai",
  "adalah",
]);

export function resolveBankRoot(explicit) {
  return explicit || process.env.GROK_DESIGN_BANK || DEFAULT_BANK;
}

export function catalogPaths(bankRoot) {
  return {
    refero: path.join(bankRoot, "Refero", "bank", "catalog.json"),
    motion: path.join(bankRoot, "motionsites", "library", "catalog.json"),
    referoRoot: path.join(bankRoot, "Refero"),
    motionRoot: path.join(bankRoot, "motionsites", "library"),
  };
}

export function requireCatalogs(bankRoot) {
  const paths = catalogPaths(bankRoot);
  const missing = [];
  if (!fs.existsSync(paths.refero)) missing.push(paths.refero);
  if (!fs.existsSync(paths.motion)) missing.push(paths.motion);
  if (missing.length) {
    const err = new Error(`Design bank catalogs missing:\n${missing.join("\n")}`);
    err.code = "BANK_MISSING";
    err.missing = missing;
    throw err;
  }
  return paths;
}

export function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

export function tokenize(text) {
  if (!text) return [];
  const raw = String(text)
    .toLowerCase()
    .replace(/[#./:_]+/g, " ")
    .match(/[a-z0-9]{3,}/g);
  if (!raw) return [];
  const out = [];
  const seen = new Set();
  for (const w of raw) {
    if (STOP.has(w) || seen.has(w)) continue;
    seen.add(w);
    out.push(w);
  }
  return out;
}

export function overlapRatio(queryTokens, docTokens) {
  if (!queryTokens.length || !docTokens.length) return 0;
  const set = new Set(docTokens);
  let hits = 0;
  for (const t of queryTokens) if (set.has(t)) hits += 1;
  return hits / queryTokens.length;
}

export function parseHex(hex) {
  if (!hex) return null;
  const m = String(hex).trim().match(/^#?([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (!m) return null;
  let h = m[1];
  if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  };
}

export function hexToHsl(hex) {
  const rgb = parseHex(hex);
  if (!rgb) return null;
  const r = rgb.r / 255;
  const g = rgb.g / 255;
  const b = rgb.b / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  if (d === 0) return { h: 0, s: 0, l };
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = 0;
  if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;
  return { h: h * 60, s, l };
}

export function isAccent(hsl) {
  if (!hsl) return false;
  if (hsl.s < 0.12) return false;
  if (hsl.l < 0.08 || hsl.l > 0.92) return false;
  return true;
}

export function hueCloseness(aHexes, bHexes) {
  const a = (aHexes || []).map(hexToHsl).filter(isAccent);
  const b = (bHexes || []).map(hexToHsl).filter(isAccent);
  if (!a.length || !b.length) return 0;
  let best = 0;
  for (const x of a) {
    for (const y of b) {
      const dh = Math.min(Math.abs(x.h - y.h), 360 - Math.abs(x.h - y.h));
      if (dh <= 30) best = Math.max(best, 1 - dh / 30);
    }
  }
  return best;
}

export function familyOf(slug) {
  return String(slug || "")
    .toLowerCase()
    .replace(/-[0-9a-f]{8}$/i, "")
    .replace(/-hero$/, "");
}

export function extractHexes(text) {
  if (!text) return [];
  const found = String(text).match(/#(?:[0-9a-f]{3}|[0-9a-f]{6})\b/gi) || [];
  const out = [];
  const seen = new Set();
  for (const hex of found) {
    const key = hex.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(key.startsWith("#") ? key : `#${key}`);
  }
  return out;
}

export function argValue(argv, name, fallback = null) {
  const i = argv.indexOf(`--${name}`);
  if (i === -1) return fallback;
  const v = argv[i + 1];
  return v && !v.startsWith("--") ? v : fallback;
}

export function hasFlag(argv, name) {
  return argv.includes(`--${name}`);
}
