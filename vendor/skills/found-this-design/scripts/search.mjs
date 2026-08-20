#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import {
  argValue,
  familyOf,
  hasFlag,
  hueCloseness,
  overlapRatio,
  readJson,
  requireCatalogs,
  resolveBankRoot,
  tokenize,
} from "./lib.mjs";
import { fingerprint } from "./fingerprint.mjs";

const MIX_THRESHOLD = 8;
const STILLS = [".webp", ".png", ".jpg", ".jpeg", ".gif"];

function loadBrief(argv, cwd) {
  const file = argValue(argv, "brief", "");
  if (file) return readJson(path.resolve(cwd, file));
  const raw = argValue(argv, "brief-json", "");
  if (raw) return JSON.parse(raw);
  return fingerprint({
    cwd,
    query: argValue(argv, "query", ""),
    count: argValue(argv, "count", "3"),
    intent: argValue(argv, "intent", ""),
  });
}

function queryTokens(brief) {
  return tokenize(
    [brief.query, brief.productName, brief.industry, brief.surface, ...(brief.kinds || [])]
      .filter(Boolean)
      .join(" "),
  );
}

function addReason(reasons, code, detail) {
  if (!detail) return;
  if (reasons.some((r) => r.code === code && r.detail === detail)) return;
  reasons.push({ code, detail });
}

function scoreRefero(style, brief, qTokens) {
  const reasons = [];
  let score = 0;
  const kinds = brief.kinds || [];
  if (kinds.includes(style.kind)) {
    score += 24;
    addReason(reasons, "kind", style.kind);
  } else if ((style.tags || []).some((t) => kinds.includes(t))) {
    score += 12;
    const tag = style.tags.find((t) => kinds.includes(t));
    addReason(reasons, "kind", tag);
  }

  if (brief.theme && brief.theme !== "unknown") {
    if (style.theme === brief.theme) {
      score += 20;
      addReason(reasons, "theme", style.theme);
    } else if (style.theme && style.theme !== brief.theme) {
      score -= 8;
    }
  }

  const doc = tokenize(
    [style.name, style.northStar, ...(style.tags || []), ...(style.fonts || []), style.industry]
      .filter(Boolean)
      .join(" "),
  );
  const tokenPts = overlapRatio(qTokens, doc) * 24;
  if (tokenPts >= 3) {
    score += tokenPts;
    addReason(reasons, "tokens", style.northStar || style.name);
  }

  if (brief.industry && style.industry) {
    const a = tokenize(brief.industry);
    const b = tokenize(style.industry);
    if (overlapRatio(a, b) > 0 || String(style.industry).toLowerCase().includes(brief.industry)) {
      score += 12;
      addReason(reasons, "industry", style.industry);
    }
  }

  const itemHexes = (style.colors || []).map((c) => c.hex).filter(Boolean);
  const hue = hueCloseness(brief.hexes || [], itemHexes);
  if (hue > 0) {
    score += hue * 10;
    addReason(reasons, "hue", "accent");
  }

  const rank = [style.trendingRank, style.popularRank].find((n) => Number.isFinite(n));
  if (Number.isFinite(rank) && rank >= 1 && rank <= 20) {
    score += 4 * ((21 - rank) / 20);
    addReason(reasons, "rank", String(rank));
  }

  if (style.thumbMissing) score -= 15;
  return { score, reasons };
}

function surfaceHit(item, surface) {
  const bag = new Set(
    [item.jenis, item.page_type, ...(item.types_source || [])].filter(Boolean),
  );
  if (bag.has(surface)) return "exact";
  if (
    (surface === "hero" && bag.has("landing-page")) ||
    (surface === "landing-page" && bag.has("hero"))
  ) {
    return "related";
  }
  return "";
}

function scoreMotion(item, brief, qTokens) {
  const reasons = [];
  let score = 0;
  const hit = surfaceHit(item, brief.surface);
  if (hit === "exact") {
    score += 28;
    addReason(reasons, "surface", item.jenis || brief.surface);
  } else if (hit === "related") {
    score += 16;
    addReason(reasons, "surface", `${item.jenis}~${brief.surface}`);
  }

  const industryBlob = [item.industry, item.category_source].filter(Boolean).join(" ");
  if (brief.industry && industryBlob) {
    const a = tokenize(brief.industry);
    const b = tokenize(industryBlob);
    if (
      overlapRatio(a, b) > 0 ||
      industryBlob.toLowerCase().includes(String(brief.industry).toLowerCase())
    ) {
      score += 20;
      addReason(reasons, "industry", item.industry || item.category_source);
    }
  }

  const tokenPts = overlapRatio(qTokens, tokenize([item.title, item.id, industryBlob].join(" "))) * 16;
  if (tokenPts >= 2) {
    score += tokenPts;
    addReason(reasons, "tokens", item.title);
  }

  if (item.featured) {
    score += 4;
    addReason(reasons, "featured", "featured");
  }
  if (Number.isFinite(item.popular_score) && item.popular_score > 0) {
    score += Math.min(4, item.popular_score / 8);
  }
  return { score, reasons };
}

function referoAbs(referoRoot, rel) {
  if (!rel) return null;
  return path.join(referoRoot, rel.replace(/^\//, ""));
}

function firstExisting(candidates) {
  for (const p of candidates) {
    if (p && fs.existsSync(p)) return p;
  }
  return candidates[0] || null;
}

function motionPreview(dir, previewField) {
  const named = previewField ? path.join(dir, previewField) : null;
  const fallbacks = STILLS.map((ext) => path.join(dir, `preview${ext}`));
  return firstExisting([named, ...fallbacks]);
}

function shapeRefero(style, scored, paths) {
  const design = referoAbs(paths.referoRoot, style.files?.design);
  const tokens = referoAbs(paths.referoRoot, style.files?.tokens);
  const tailwind = referoAbs(paths.referoRoot, style.files?.tailwind);
  const thumb = referoAbs(paths.referoRoot, style.thumb);
  const dir = design ? path.dirname(design) : null;
  return {
    id: style.slug || style.id,
    bank: "refero",
    name: style.name,
    lane: "identity",
    score: Number(scored.score.toFixed(2)),
    reasons: scored.reasons,
    theme: style.theme || null,
    kind: style.kind || null,
    jenis: null,
    northStar: style.northStar || null,
    industry: style.industry || null,
    fonts: style.fonts || [],
    hexes: (style.colors || []).map((c) => c.hex).filter(Boolean).slice(0, 8),
    preview: thumb,
    files: {
      design,
      tokens,
      tailwind,
      meta: dir ? path.join(dir, "meta.json") : null,
      prompt: null,
    },
  };
}

function shapeMotion(item, scored, paths) {
  const dir = path.join(paths.motionRoot, item.jenis, item.id);
  return {
    id: item.id,
    bank: "motion",
    name: item.title || item.id,
    lane: "section",
    score: Number(scored.score.toFixed(2)),
    reasons: scored.reasons,
    theme: null,
    kind: null,
    jenis: item.jenis,
    northStar: null,
    industry: item.industry || item.category_source || null,
    fonts: [],
    hexes: [],
    preview: motionPreview(dir, item.preview),
    files: {
      design: null,
      tokens: null,
      tailwind: null,
      meta: path.join(dir, "meta.json"),
      prompt: path.join(dir, "prompt.md"),
    },
  };
}

function takeDiverse(sorted, count, used) {
  const out = [];
  for (const item of sorted) {
    if (out.length >= count) break;
    const fam = familyOf(item.id);
    if (used.has(fam)) continue;
    used.add(fam);
    out.push(item);
  }
  return out;
}

function pickShortlist(refero, motion, count, lane) {
  const used = new Set();
  if (lane === "identity") return takeDiverse(refero, count, used);
  if (lane === "section") return takeDiverse(motion, count, used);

  const referoHits = refero.filter((x) => x.score >= MIX_THRESHOLD);
  const motionHits = motion.filter((x) => x.score >= MIX_THRESHOLD);
  const out = [];
  if (referoHits.length && motionHits.length) {
    out.push(...takeDiverse(referoHits, 1, used));
    out.push(...takeDiverse(motionHits, 1, used));
  }
  const merged = [...referoHits, ...motionHits].sort((a, b) => b.score - a.score);
  for (const item of merged) {
    if (out.length >= count) break;
    if (out.includes(item)) continue;
    const fam = familyOf(item.id);
    if (used.has(fam)) continue;
    used.add(fam);
    out.push(item);
  }
  if (out.length < count) {
    const rest = [...refero, ...motion].sort((a, b) => b.score - a.score);
    for (const item of rest) {
      if (out.length >= count) break;
      if (out.includes(item)) continue;
      const fam = familyOf(item.id);
      if (used.has(fam)) continue;
      used.add(fam);
      out.push(item);
    }
  }
  return out.sort((a, b) => b.score - a.score);
}

export function search({ brief, bankRoot, lane, exclude = [] }) {
  const root = resolveBankRoot(bankRoot);
  const paths = requireCatalogs(root);
  const referoCat = readJson(paths.refero);
  const motionCat = readJson(paths.motion);
  const qTokens = queryTokens(brief);
  const skip = new Set((exclude || []).map((s) => String(s).toLowerCase()));
  const resolvedLane = lane || brief.laneHint || "both";

  const refero = [];
  for (const style of referoCat.styles || []) {
    const id = style.slug || style.id;
    if (skip.has(String(id).toLowerCase())) continue;
    const scored = scoreRefero(style, brief, qTokens);
    refero.push(shapeRefero(style, scored, paths));
  }
  refero.sort((a, b) => b.score - a.score);

  const motion = [];
  for (const item of motionCat.items || []) {
    if (skip.has(String(item.id).toLowerCase())) continue;
    const scored = scoreMotion(item, brief, qTokens);
    motion.push(shapeMotion(item, scored, paths));
  }
  motion.sort((a, b) => b.score - a.score);

  const count = Number(brief.count) === 5 ? 5 : 3;
  const items = pickShortlist(refero, motion, count, resolvedLane);
  return {
    bankRoot: root,
    lane: resolvedLane,
    count,
    brief: {
      intent: brief.intent,
      mode: brief.mode,
      surface: brief.surface,
      industry: brief.industry,
      theme: brief.theme,
      kinds: brief.kinds,
      productName: brief.productName,
    },
    items,
  };
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function selfTest(bankRoot) {
  const fixturesDir = path.join(path.dirname(new URL(import.meta.url).pathname), "fixtures");
  const saas = readJson(path.join(fixturesDir, "saas-dark-dashboard.json"));
  const wellness = readJson(path.join(fixturesDir, "wellness-hero.json"));

  const saasHit = search({ brief: saas, bankRoot, lane: "identity" });
  assert(saasHit.items.length === 3, `saas expected 3, got ${saasHit.items.length}`);
  const darkish = saasHit.items.filter(
    (i) => i.theme === "dark" || i.kind === "dark-mode" || (i.kind === "minimal" && i.theme === "dark"),
  );
  assert(
    darkish.length >= 2,
    `saas dark dashboard should lean Refero dark/minimal, got ${saasHit.items.map((i) => `${i.id}:${i.kind}/${i.theme}`).join(", ")}`,
  );

  const well = search({ brief: wellness, bankRoot, lane: "section" });
  assert(well.items.length === 3, `wellness expected 3, got ${well.items.length}`);
  const motionOk = well.items.filter(
    (i) =>
      i.bank === "motion" &&
      (i.jenis === "hero" || i.jenis === "landing-page" || /well|health|heal|mind|body/i.test(i.id + i.name)),
  );
  assert(
    motionOk.length >= 2,
    `wellness hero should lean Motion hero/landing, got ${well.items.map((i) => `${i.id}:${i.jenis}`).join(", ")}`,
  );

  const five = search({ brief: { ...saas, count: 5 }, bankRoot, lane: "both" });
  assert(five.items.length === 5, `count 5 expected 5, got ${five.items.length}`);
  const banks = new Set(five.items.map((i) => i.bank));
  assert(banks.has("refero") && banks.has("motion"), "lane both should mix banks");

  const missingRoot = path.join(path.dirname(fixturesDir), "missing-bank-should-not-exist");
  let failed = false;
  try {
    search({ brief: saas, bankRoot: missingRoot });
  } catch (err) {
    failed = err.code === "BANK_MISSING";
  }
  assert(failed, "missing catalog should exit with BANK_MISSING");

  process.stdout.write("self-test ok\n");
}

const isMain =
  import.meta.url === `file://${path.resolve(process.argv[1] || "")}`;

if (isMain) {
  const argv = process.argv.slice(2);
  const cwd = argValue(argv, "cwd", process.cwd());
  const bankRoot = resolveBankRoot(argValue(argv, "bank", ""));
  try {
    if (hasFlag(argv, "self-test")) {
      selfTest(bankRoot);
      process.exit(0);
    }
    const brief = loadBrief(argv, cwd);
    const countOverride = argValue(argv, "count", "");
    if (countOverride) brief.count = Number(countOverride) === 5 ? 5 : 3;
    const exclude = (argValue(argv, "exclude", "") || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const result = search({
      brief,
      bankRoot,
      lane: argValue(argv, "lane", brief.laneHint || "both"),
      exclude,
    });
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } catch (err) {
    process.stderr.write(`${err.message}\n`);
    process.exit(err.code === "BANK_MISSING" ? 2 : 1);
  }
}
