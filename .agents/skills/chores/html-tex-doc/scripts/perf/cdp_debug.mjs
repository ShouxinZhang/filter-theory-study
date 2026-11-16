#!/usr/bin/env node
/* 全自动定位布局固定开销：无头 Chrome + DevTools 协议。
 *   node cdp_debug.mjs <url> <step> [out.json]
 * step: sheets | rules | trace | eval:<js 表达式>
 */
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, step = "sheets", outFile] = process.argv.slice(2);
const PORT = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(process.env.CDP_TMP || tmpdir(), "cdp-"));
const chrome = spawn("google-chrome", [
  ...(process.env.HEADED ? [] : ["--headless=new"]), `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  "--window-size=1024,768", "--no-first-run", "--no-default-browser-check", "--disable-extensions", ...(process.env.CHROME_FLAGS ? process.env.CHROME_FLAGS.split(" ") : []), "about:blank",
], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function connect() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch (e) {}
    await sleep(200);
  }
  throw new Error("Chrome 未就绪");
}

const ws = new WebSocket(await connect());
await new Promise((r) => (ws.onopen = r));
let seq = 0;
const pending = new Map(), listeners = [];
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
  else listeners.forEach((f) => f(m));
};
const send = (method, params = {}) => new Promise((res, rej) => { const id = ++seq; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
const evaluate = async (expr) => {
  const r = await send("Runtime.evaluate", { expression: `(async () => { ${expr} })()`, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
};

const PRELUDE = `
  const d = document.createElement('div'); d.style.cssText = 'position:fixed;left:0;top:0'; d.textContent = 'x';
  const once = () => { const a = performance.now(); document.body.appendChild(d); d.offsetHeight; const r = performance.now() - a; d.remove(); d.offsetHeight; return r; };
  const cost = () => { once(); return +Math.min(once(), once(), once()).toFixed(2); };
`;

let result;
try {
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Page.navigate", { url });
  await sleep(1500);
  await evaluate("for (let i = 0; i < 30 && !(window.MathJax && MathJax.startup && MathJax.startup.promise); i++) await new Promise(r => setTimeout(r, 100)); if (window.MathJax && MathJax.startup) await MathJax.startup.promise; await new Promise(r => setTimeout(r, 1500));");
  const info = await evaluate(`${PRELUDE} return { nodes: document.getElementsByTagName('*').length, mjx: document.querySelectorAll('mjx-container').length, base: cost(), ua: navigator.userAgent };`);

  if (process.env.INJECT_CSS) {
    await evaluate(`const s = document.createElement('style'); s.textContent = ${JSON.stringify(process.env.INJECT_CSS)}; document.head.appendChild(s); document.body.offsetHeight; await new Promise(r => setTimeout(r, 800)); return 1;`);
  }
  if (step === "sheets") {
    result = await evaluate(`${PRELUDE}
      const out = [];
      for (const s of document.styleSheets) {
        let n = -1; try { n = s.cssRules.length; } catch (e) {}
        const owner = s.ownerNode; const name = s.href || owner.id || owner.outerHTML.slice(0, 60);
        s.disabled = true; document.body.offsetHeight; const off = cost(); s.disabled = false; document.body.offsetHeight;
        out.push({ name, rules: n, costWhenDisabled: off });
      }
      return out;`);
  } else if (step === "rules") {
    result = await evaluate(`${PRELUDE}
      const base = cost(), out = [];
      for (const s of document.styleSheets) {
        let rules; try { rules = s.cssRules; } catch (e) { continue; }
        const name = s.href || s.ownerNode.id || 'inline';
        for (let i = 0; i < rules.length; i++) {
          const text = rules[i].cssText;
          s.deleteRule(i); document.body.offsetHeight;
          const c = cost();
          s.insertRule(text, i);
          if (c < base * 0.8) out.push({ sheet: name, i, cost: c, rule: text.slice(0, 300) });
        }
      }
      document.body.offsetHeight;
      return { base, after: cost(), hits: out };`);
  } else if (step === "trace") {
    const events = [];
    listeners.push((m) => { if (m.method === "Tracing.dataCollected") events.push(...m.params.value); });
    const done = new Promise((r) => listeners.push((m) => { if (m.method === "Tracing.tracingComplete") r(); }));
    await send("Tracing.start", {
      transferMode: "ReportEvents",
      traceConfig: { includedCategories: ["devtools.timeline", "disabled-by-default-devtools.timeline", "disabled-by-default-devtools.timeline.invalidationTracking", "blink", "blink.user_timing", "disabled-by-default-layout", "layout"] },
    });
    await evaluate(`${PRELUDE} performance.mark('probe-start'); for (let i = 0; i < 3; i++) once(); performance.mark('probe-end'); return 1;`);
    await send("Tracing.end");
    await done;
    const layouts = events.filter((e) => e.name === "Layout" && (e.ph === "X" || e.ph === "B"));
    const byName = {};
    for (const e of events) if (e.ph === "X" && e.dur) { const k = `${e.cat}|${e.name}`; (byName[k] ??= { n: 0, ms: 0 }); byName[k].n++; byName[k].ms += e.dur / 1000; }
    const top = Object.entries(byName).sort((a, b) => b[1].ms - a[1].ms).slice(0, 25).map(([k, v]) => ({ k, n: v.n, ms: +v.ms.toFixed(1) }));
    const inval = {};
    for (const e of events) if (/Invalidation|ScheduleStyle|InvalidateLayout/.test(e.name)) {
      const d = e.args?.data || {}; const k = `${e.name}|${d.reason || ""}|${d.nodeName || ""}`; inval[k] = (inval[k] || 0) + 1;
    }
    result = {
      events: events.length,
      layouts: layouts.map((e) => ({ ms: e.dur ? +(e.dur / 1000).toFixed(1) : null, begin: e.args?.beginData && { dirtyObjects: e.args.beginData.dirtyObjects, totalObjects: e.args.beginData.totalObjects, partialLayout: e.args.beginData.partialLayout }, end: e.args?.endData && Object.keys(e.args.endData) })),
      top, invalidations: Object.entries(inval).sort((a, b) => b[1] - a[1]).slice(0, 25),
    };
    if (outFile && process.env.KEEP_TRACE) writeFileSync(outFile.replace(/\.json$/, ".trace.json"), JSON.stringify(events));
  } else if (step === "ax") {
    const probe = `${PRELUDE} const sc = document.scrollingElement; const t = (f) => { const a = performance.now(); f(); document.body.offsetHeight; return +(performance.now() - a).toFixed(1); };
      return { append: [once(), once(), once(), once()].map(x => +x.toFixed(1)), scroll: [t(() => { sc.scrollTop += 3000; }), t(() => { sc.scrollTop += 3000; })] };`;
    const before = await evaluate(probe);
    await send("Accessibility.enable");
    await send("Accessibility.getFullAXTree");
    await sleep(1500);
    const withAx = await evaluate(probe);
    await sleep(1000);
    const withAx2 = await evaluate(probe);
    await send("Accessibility.disable");
    await sleep(1500);
    const after = await evaluate(probe);
    result = { before, withAx, withAx2, afterDisable: after };
  } else if (step === "scroll") {
    /* 真实合成器滚动（模拟滚轮手势）+ 性能录制：统计帧间隔、掉帧与主线程各类事件耗时 */
    const events = [];
    listeners.push((m) => { if (m.method === "Tracing.dataCollected") events.push(...m.params.value); });
    const done = new Promise((r) => listeners.push((m) => { if (m.method === "Tracing.tracingComplete") r(); }));
    const env = await evaluate("return { dpr: devicePixelRatio, vp: [innerWidth, innerHeight], gpu: (() => { try { const g = document.createElement('canvas').getContext('webgl'); const e = g.getExtension('WEBGL_debug_renderer_info'); return g.getParameter(e.UNMASKED_RENDERER_WEBGL); } catch (e) { return String(e); } })() };");
    await evaluate("window.__fr = []; window.__on = true; let t = performance.now(); const tick = () => { const u = performance.now(); __fr.push(u - t); t = u; if (__on) requestAnimationFrame(tick); }; requestAnimationFrame(tick); return 1;");
    await sleep(600);
    const idle = await evaluate("const a = __fr.splice(0); return a;");
    await send("Tracing.start", { transferMode: "ReportEvents", traceConfig: { includedCategories: ["devtools.timeline", "disabled-by-default-devtools.timeline", "disabled-by-default-devtools.timeline.frame", "benchmark", "cc", "viz"] } });
    const phases = {};
    for (const [name, dist, speed] of [["slow", -6000, 1500], ["fast", -20000, 12000], ["back", 26000, 30000]]) {
      await evaluate("__fr.splice(0); return 1;");
      await send("Input.synthesizeScrollGesture", { x: 500, y: 400, yDistance: dist, speed, gestureSourceType: "mouse" });
      phases[name] = await evaluate("return __fr.splice(0);");
    }
    await evaluate("__on = false; return 1;");
    await send("Tracing.end");
    await done;
    const st = (a) => { const s = [...a].sort((x, y) => x - y), n = s.length; return n ? { n, med: +s[n >> 1].toFixed(1), p90: +s[Math.floor(n * 0.9)].toFixed(1), p99: +s[Math.floor(n * 0.99)].toFixed(1), max: +s[n - 1].toFixed(1), over25: s.filter((x) => x > 25).length, over50: s.filter((x) => x > 50).length } : null; };
    const byName = {};
    for (const e of events) if (e.ph === "X" && e.dur) { const k = e.name; (byName[k] ??= { n: 0, ms: 0, max: 0 }); byName[k].n++; byName[k].ms += e.dur / 1000; byName[k].max = Math.max(byName[k].max, e.dur / 1000); }
    const top = Object.entries(byName).sort((a, b) => b[1].ms - a[1].ms).slice(0, 22).map(([k, v]) => `${k}: n=${v.n} total=${v.ms.toFixed(0)}ms max=${v.max.toFixed(1)}ms`);
    const count = (n) => events.filter((e) => e.name === n).length;
    result = { env, idle: st(idle), slow: st(phases.slow), fast: st(phases.fast), back: st(phases.back),
      frames: { DrawFrame: count("DrawFrame"), DroppedFrame: count("DroppedFrame"), BeginFrame: count("BeginFrame") }, top };
    if (outFile && process.env.KEEP_TRACE) writeFileSync(outFile.replace(/\.json$/, ".trace.json"), JSON.stringify(events));
  } else if (step.startsWith("shot:")) {
    /* shot:<css 选择器> —— 把该元素滚到视口上方 80px 处并截图（PNG 写到 outFile） */
    const sel = step.slice(5);
    await send("Emulation.setDeviceMetricsOverride", { width: 1100, height: 900, deviceScaleFactor: 2, mobile: false });
    result = await evaluate(`const el = document.querySelector(${JSON.stringify(sel)}); if (!el) return 'no element'; window.scrollTo(0, el.getBoundingClientRect().top + scrollY - 80); await new Promise(r => setTimeout(r, 2500)); const m = document.querySelector('main mjx-container'); return { y: Math.round(scrollY), mjxFont: getComputedStyle(m).fontSize, parentFont: getComputedStyle(m.parentElement).fontSize, firstEqH: document.querySelector('div.eq').getBoundingClientRect().height };`);
    const shot = await send("Page.captureScreenshot", { format: "png" });
    if (outFile) writeFileSync(outFile.replace(/\.json$/, ".png"), Buffer.from(shot.data, "base64"));
  } else if (step.startsWith("shotjs:")) {
    /* shotjs:<异步 JS> —— 固定视口，执行 JS 把页面带到某个状态后截图（PNG 写到 outFile 同名 .png） */
    await send("Emulation.setDeviceMetricsOverride", { width: 1100, height: 900, deviceScaleFactor: 1, mobile: false });
    result = await evaluate(`${step.slice(7)}; await new Promise(r => setTimeout(r, 900)); document.activeElement && document.activeElement.blur(); return { y: Math.round(scrollY), h: document.scrollingElement.scrollHeight };`);
    const shot = await send("Page.captureScreenshot", { format: "png" });
    if (outFile) writeFileSync(outFile.replace(/\.json$/, ".png"), Buffer.from(shot.data, "base64"));
  } else if (step.startsWith("eval:")) {
    result = await evaluate(`${PRELUDE} ${step.slice(5)}`);
  }
  result = { info, step, result };
} catch (e) {
  result = { error: String(e) };
} finally {
  ws.close();
  chrome.kill();
}
const text = JSON.stringify(result, null, 1);
if (outFile) writeFileSync(outFile, text);
console.log(text.length > 9000 ? text.slice(0, 9000) + "\n…(截断)" : text);
process.exit(0);
