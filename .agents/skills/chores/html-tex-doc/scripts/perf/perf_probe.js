/* html-tex-doc 页面性能探针。用法：把本文件放进站点输出目录，在页面控制台执行
 *   await import("/perf_probe.js"); JSON.stringify(await __probe.all())
 * 各项也可单独调用：__probe.env() / load() / sync() / hover() / frames()
 * 帧间隔只有在窗格可见时才有意义；rAF 不触发时 frames() 返回 {skipped: true}。 */
(() => {
  const now = () => performance.now();
  const r1 = (x) => Math.round(x * 10) / 10;
  const force = () => document.body.offsetHeight;
  const timed = (f) => { const t = now(); f(); force(); return r1(now() - t); };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const raf = (limit = 400) => new Promise((res) => {
    const to = setTimeout(() => res(false), limit);
    requestAnimationFrame(() => { clearTimeout(to); res(true); });
  });
  const stats = (a) => {
    const s = [...a].sort((x, y) => x - y), n = s.length;
    return { n, med: r1(s[n >> 1]), p90: r1(s[Math.floor(n * 0.9)]), max: r1(s[n - 1]), over20: s.filter((x) => x > 20).length, over50: s.filter((x) => x > 50).length };
  };
  const root = document.documentElement;
  const pane = () => document.getElementById("doc-root") || document.body;
  const scroller = () => {
    const p = pane();
    return p !== document.body && p.scrollHeight > p.clientHeight + 4 && getComputedStyle(p).overflowY !== "visible" ? p : document.scrollingElement;
  };

  const longtasks = [];
  try {
    new PerformanceObserver((l) => l.getEntries().forEach((e) => longtasks.push([Math.round(e.startTime), Math.round(e.duration)])))
      .observe({ type: "longtask", buffered: true });
  } catch (e) {}

  function env() {
    return {
      url: location.pathname, hidden: document.hidden, dpr: devicePixelRatio, viewport: [innerWidth, innerHeight],
      nodes: document.getElementsByTagName("*").length,
      mjx: document.querySelectorAll("mjx-container").length,
      mjxNodes: document.querySelectorAll("mjx-container *").length,
      svgNodes: document.querySelectorAll("svg *").length,
      height: scroller().scrollHeight, cssRules: Array.from(document.styleSheets).reduce((n, s) => { try { return n + s.cssRules.length; } catch (e) { return n; } }, 0),
    };
  }

  async function load() {
    const t0 = now();
    if (window.MathJax?.startup?.promise) await MathJax.startup.promise;
    await sleep(300);
    const nav = performance.getEntriesByType("navigation")[0];
    const paint = Object.fromEntries(performance.getEntriesByType("paint").map((p) => [p.name, Math.round(p.startTime)]));
    return {
      dcl: Math.round(nav.domContentLoadedEventEnd), loadEvent: Math.round(nav.loadEventEnd), paint,
      mathjaxReadyAt: Math.round(t0), longtasks: longtasks.slice(),
      longtaskTotal: longtasks.reduce((s, x) => s + x[1], 0), transferKB: Math.round(nav.encodedBodySize / 1024),
    };
  }

  function sync() {
    const out = {};
    out.layoutClean = timed(() => {});
    out.rootClassToggle = timed(() => root.classList.add("ctrl-aiming")); timed(() => root.classList.remove("ctrl-aiming"));
    out.paneClassToggle = timed(() => pane().classList.add("probe-x")); timed(() => pane().classList.remove("probe-x"));
    const th = root.getAttribute("data-theme");
    out.themeToggle = timed(() => root.setAttribute("data-theme", th === "light" ? "dark" : "light"));
    timed(() => (th ? root.setAttribute("data-theme", th) : root.removeAttribute("data-theme")));
    const m = root.style.getPropertyValue("--measure");
    out.relayoutAll = timed(() => root.style.setProperty("--measure", "700px"));
    timed(() => (m ? root.style.setProperty("--measure", m) : root.style.removeProperty("--measure")));
    const sc = scroller(), y = sc.scrollTop;
    out.scrollThenLayout = timed(() => { sc.scrollTop = (y + sc.scrollHeight / 2) % sc.scrollHeight; });
    sc.scrollTop = y; force();
    out.bodyAppendDiv = timed(() => { const d = document.createElement("div"); d.textContent = "x"; document.body.appendChild(d); });
    document.body.lastChild.remove(); force();
    return out;
  }

  /* 悬停预览：走 reader.js 的真实事件路径，测 "定时器触发 → 弹层就位" 这一段同步耗时。 */
  async function hover(repeat = 2) {
    const pop = document.querySelector(".xref-preview");
    if (!pop) return { skipped: "no .xref-preview" };
    const seen = {}, out = {};
    for (const a of pane().querySelectorAll('a[href^="#"]')) {
      if (a.closest("nav.toc")) continue;
      const tg = document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)));
      if (!tg) continue;
      const kind = tg.tagName.toLowerCase() + (tg.classList[0] ? "." + tg.classList[0] : "");
      if (seen[kind]) continue;
      seen[kind] = 1;
      const runs = [];
      for (let i = 0; i < repeat; i++) {
        const lt0 = longtasks.length;
        let cost = null;
        const mo = new MutationObserver(() => {});
        // 用同步包装测量：在 show() 的 setTimeout 之前后各插一个 0ms 宏任务不可行，改为直接计时 class 变化前后的任务
        const t0 = now();
        a.dispatchEvent(new PointerEvent("pointerover", { bubbles: true, pointerType: "mouse" }));
        while (!pop.classList.contains("show") && now() - t0 < 3000) await sleep(20);
        const tShown = now();
        force();
        cost = r1(now() - tShown);
        runs.push({ shown: pop.classList.contains("show"), settleLayout: cost, longtasks: longtasks.slice(lt0).map((x) => x[1]), popNodes: pop.getElementsByTagName("*").length });
        mo.disconnect();
        a.dispatchEvent(new PointerEvent("pointerout", { bubbles: true, pointerType: "mouse" }));
        while (pop.classList.contains("show") && now() - tShown < 3000) await sleep(20);
      }
      out[kind] = runs;
    }
    return out;
  }

  /* 直接计时预览的三个同步步骤（克隆 / 插入并测量 / 显示），不经过定时器。 */
  function hoverSteps() {
    const pop = document.querySelector(".xref-preview");
    if (!pop) return { skipped: "no .xref-preview" };
    const seen = {}, out = {};
    for (const a of pane().querySelectorAll('a[href^="#"]')) {
      if (a.closest("nav.toc")) continue;
      const tg = document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)));
      if (!tg) continue;
      const kind = tg.tagName.toLowerCase() + (tg.classList[0] ? "." + tg.classList[0] : "");
      if (seen[kind]) continue;
      seen[kind] = 1;
      force();
      const t0 = now();
      const c = tg.cloneNode(true);
      const t1 = now();
      pop.replaceChildren(c);
      pop.getBoundingClientRect();
      const t2 = now();
      pop.classList.add("show"); force();
      const t3 = now();
      out[kind] = { clone: r1(t1 - t0), insertMeasure: r1(t2 - t1), show: r1(t3 - t2), nodes: c.getElementsByTagName("*").length + 1 };
      pop.classList.remove("show"); pop.replaceChildren(); force();
    }
    return out;
  }

  async function frames() {
    if (!(await raf())) return { skipped: true, reason: "requestAnimationFrame 未触发（窗格隐藏或窗口不可见）" };
    const sc = scroller(), y0 = sc.scrollTop, out = {};
    const run = async (step, n) => {
      const fr = [];
      sc.scrollTop = 0; await raf(); await raf();
      let t = now();
      for (let i = 0; i < n; i++) {
        sc.scrollTop += step;
        if (!(await raf(1000))) return { aborted: i };
        const u = now(); fr.push(u - t); t = u;
      }
      return stats(fr);
    };
    const idle = [];
    let t = now();
    for (let i = 0; i < 30; i++) { await raf(); const u = now(); idle.push(u - t); t = u; }
    out.idle = stats(idle);
    out.smooth120 = await run(120, 150);
    out.fast600 = await run(600, 60);
    out.jump4000 = await run(4000, 12);
    sc.scrollTop = y0;
    return out;
  }

  async function all() {
    return { env: env(), load: await load(), sync: sync(), hoverSteps: hoverSteps(), frames: await frames() };
  }

  window.__probe = { env, load, sync, hover, hoverSteps, frames, all, longtasks };
})();
