#!/usr/bin/env node
/* Batch TeX -> self-contained SVG path renderer for html-tex-doc/charts.
 * Reuses mathjax-full installed in ../../scripts/node_modules.
 * stdin : {"items": ["\\kappa", "x_{21}", "\\times 10^{-3}"]}
 * stdout: {"version": "...", "items": [{"vb": [x,y,w,h], "w_ex": ..., "h_ex": ..., "va_ex": ..., "inner": "..."}]}
 */
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const parentPkg = resolve(here, "../../scripts/package.json");
const require = createRequire(parentPkg);

const { mathjax } = require("mathjax-full/js/mathjax.js");
const { TeX } = require("mathjax-full/js/input/tex.js");
const { SVG } = require("mathjax-full/js/output/svg.js");
const { liteAdaptor } = require("mathjax-full/js/adaptors/liteAdaptor.js");
const { RegisterHTMLHandler } = require("mathjax-full/js/handlers/html.js");
const { AllPackages } = require("mathjax-full/js/input/tex/AllPackages.js");

const job = JSON.parse(readFileSync(0, "utf8"));
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);

const tex = new TeX({
  packages: AllPackages,
  macros: { bm: ["\\boldsymbol{#1}", 1], ...(job.macros || {}) },
  tags: "none",
});
// fontCache: 'none' keeps every formula 100% self-contained with zero <defs> ID collisions
const svg = new SVG({ fontCache: "none" });
const doc = mathjax.document("", { InputJax: tex, OutputJax: svg });

const parseEx = (s) => {
  const m = String(s || "").match(/(-?\d+(?:\.\d+)?)ex/);
  return m ? parseFloat(m[1]) : 0.0;
};

const items = (job.items || []).map((src) => {
  const node = doc.convert(String(src), { display: false, em: 16, ex: 8, containerWidth: 80 * 16 });
  const html = adaptor.outerHTML(node);
  const svgMatch = html.match(/<svg([^>]*)>([\s\S]*?)<\/svg>/);
  if (!svgMatch) {
    return { vb: [0, 0, 0, 0], w_ex: 0, h_ex: 0, va_ex: 0, inner: "" };
  }
  const attrs = svgMatch[1];
  const inner = svgMatch[2];
  const vbM = attrs.match(/viewBox="([^"]+)"/);
  const wM = attrs.match(/\bwidth="([^"]+)"/);
  const hM = attrs.match(/\bheight="([^"]+)"/);
  const vaM = attrs.match(/vertical-align:\s*([^;"]+)/);
  const vb = vbM ? vbM[1].trim().split(/\s+/).map(Number) : [0, 0, 0, 0];
  return {
    vb,
    w_ex: parseEx(wM && wM[1]),
    h_ex: parseEx(hM && hM[1]),
    va_ex: parseEx(vaM && vaM[1]),
    inner,
  };
});

process.stdout.write(
  JSON.stringify({
    version: require("mathjax-full/package.json").version,
    items,
  })
);
