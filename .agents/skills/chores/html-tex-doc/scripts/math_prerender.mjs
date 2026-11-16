#!/usr/bin/env node
/* 构建期公式预渲染（由 math_prerender.py 调用，不直接使用）。
 * stdin : {"macros": {...}, "fontURL": "...", "items": [{"tex": "...", "display": true}, ...], "css": true}
 * stdout: {"version": "3.2.2", "html": ["<mjx-container ...>", ...], "css": "..."}
 * 每条公式独立转换、互不依赖，因此结果可以逐条缓存。 */
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";

const require = createRequire(import.meta.url);
const { mathjax } = require("mathjax-full/js/mathjax.js");
const { TeX } = require("mathjax-full/js/input/tex.js");
const { CHTML } = require("mathjax-full/js/output/chtml.js");
const { liteAdaptor } = require("mathjax-full/js/adaptors/liteAdaptor.js");
const { RegisterHTMLHandler } = require("mathjax-full/js/handlers/html.js");
const { AllPackages } = require("mathjax-full/js/input/tex/AllPackages.js");

const job = JSON.parse(readFileSync(0, "utf8"));
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const tex = new TeX({ packages: AllPackages, macros: job.macros || {}, tags: "none" });
// adaptiveCSS: false —— 样式表不随"本次用到哪些字形"变化，缓存命中的公式才不会缺样式
const chtml = new CHTML({ fontURL: job.fontURL, adaptiveCSS: false });
const doc = mathjax.document("", { InputJax: tex, OutputJax: chtml });

const html = job.items.map(({ tex: src, display }) =>
  adaptor.outerHTML(doc.convert(src, { display, em: 16, ex: 8, containerWidth: 80 * 16 })));
const css = job.css ? adaptor.textContent(chtml.styleSheet(doc)) : "";
process.stdout.write(JSON.stringify({ version: require("mathjax-full/package.json").version, html, css }));
