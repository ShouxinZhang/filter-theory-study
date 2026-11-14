/* 阅读器增强（无依赖）：
 *  1. 栏宽：默认随窗口自适应；拖拽正文两侧手柄可手动调整，双击手柄或点“宽度”按钮恢复；记忆于 localStorage。
 *  2. 主题：自动 / 浅色 / 深色 三态切换；记忆于 localStorage。
 *  3. 链接悬停预览：鼠标停在页内链接（含 TeX 生成的 SVG 内链接）上，弹出目标内容的实时副本，
 *     类似 PDF 阅读器（Evince 等）的链接预览；预览框内的链接仍可点击跳转。
 */
(() => {
  "use strict";
  const root = document.documentElement;
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} },
  };
  const XLINK = "http://www.w3.org/1999/xlink";

  /* ---------------- 1. 栏宽 ---------------- */
  const MIN_PX = 420;
  const applyMeasure = (px) => {
    if (px == null) root.style.removeProperty("--measure");
    else root.style.setProperty("--measure", `${Math.round(px)}px`);
  };
  applyMeasure(store.get("reader.measure") && Number(store.get("reader.measure")));

  function setupResize() {
    const badge = document.createElement("div");
    badge.className = "measure-badge";
    document.body.appendChild(badge);
    for (const side of ["left", "right"]) {
      const h = document.createElement("div");
      h.className = `measure-handle ${side}`;
      h.title = "拖拽调整栏宽；双击恢复自适应";
      document.body.appendChild(h);
      h.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        h.setPointerCapture(e.pointerId);
        const startX = e.clientX, startW = document.body.getBoundingClientRect().width;
        const sign = side === "right" ? 1 : -1;
        document.body.classList.add("resizing");
        const fontPx = parseFloat(getComputedStyle(document.body).fontSize);
        const move = (ev) => {
          // 正文居中，两侧同时伸缩，故位移乘 2
          const w = Math.max(MIN_PX, Math.min(window.innerWidth, startW + 2 * sign * (ev.clientX - startX)));
          applyMeasure(w);
          badge.textContent = `${Math.round(w)} px · 约 ${Math.round((w - 2 * 32) / fontPx)} 字/行`;
        };
        const up = () => {
          document.body.classList.remove("resizing");
          h.removeEventListener("pointermove", move);
          const v = root.style.getPropertyValue("--measure");
          if (v) store.set("reader.measure", parseFloat(v));
        };
        h.addEventListener("pointermove", move);
        h.addEventListener("pointerup", up, { once: true });
        h.addEventListener("pointercancel", up, { once: true });
      });
      h.addEventListener("dblclick", resetMeasure);
    }
  }
  function resetMeasure() { applyMeasure(null); store.set("reader.measure", null); }

  /* ---------------- 2. 主题 ---------------- */
  const THEMES = ["auto", "light", "dark"];
  const THEME_LABEL = { auto: "◐ 自动", light: "☀ 浅色", dark: "☾ 深色" };
  const applyTheme = (t) => { t === "auto" ? root.removeAttribute("data-theme") : root.setAttribute("data-theme", t); };
  let theme = THEMES.includes(store.get("reader.theme")) ? store.get("reader.theme") : "auto";
  applyTheme(theme);

  function setupBar() {
    const bar = document.createElement("div");
    bar.className = "reader-bar";
    const tBtn = document.createElement("button");
    tBtn.textContent = THEME_LABEL[theme];
    tBtn.title = "切换主题：自动（跟随系统）/ 浅色 / 深色";
    tBtn.onclick = () => {
      theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
      applyTheme(theme); store.set("reader.theme", theme); tBtn.textContent = THEME_LABEL[theme];
    };
    const wBtn = document.createElement("button");
    wBtn.textContent = "↔ 宽度";
    wBtn.title = "恢复自适应栏宽（也可拖拽正文两侧边缘调整）";
    wBtn.onclick = resetMeasure;
    bar.append(tBtn, wBtn);
    document.body.appendChild(bar);
  }

  /* ---------------- 3. 链接悬停预览 ---------------- */
  const SHOW_DELAY = 280, HIDE_DELAY = 220;
  let pop, showTimer, hideTimer, current;

  const hrefOf = (a) => a.getAttribute("href") || a.getAttributeNS(XLINK, "href") || "";
  const isHeading = (el) => /^H[1-6]$/.test(el.tagName);

  function buildPreview(id) {
    const target = document.getElementById(id);
    if (!target) return null;
    const nodes = [target];
    if (isHeading(target)) {            // 章节：标题 + 随后最多两个块
      let n = target.nextElementSibling;
      while (n && nodes.length < 3 && !isHeading(n)) { nodes.push(n); n = n.nextElementSibling; }
    } else if (target.matches("div.thm") && target.nextElementSibling?.matches("div.proof")) {
      nodes.push(target.nextElementSibling);
    }
    const box = document.createElement("div");
    for (const n of nodes) {
      const c = n.cloneNode(true);
      // 去掉副本中的 id，避免重复锚点；SVG 中 <use> 仍引用原文档里的字形定义，可正常显示
      c.removeAttribute("id");
      c.querySelectorAll("[id]").forEach((e) => e.removeAttribute("id"));
      box.appendChild(c);
    }
    return box;
  }

  function place(anchorEl) {
    const r = anchorEl.getBoundingClientRect(), gap = 8, vw = window.innerWidth, vh = window.innerHeight;
    pop.style.left = "0px"; pop.style.top = "0px";
    const pr = pop.getBoundingClientRect();
    let left = Math.min(Math.max(8, r.left + r.width / 2 - pr.width / 2), vw - pr.width - 8);
    let top = r.bottom + gap;                                  // 优先放在下方
    if (top + pr.height > vh - 8 && r.top - gap - pr.height > 8) top = r.top - gap - pr.height;
    top = Math.max(8, Math.min(top, vh - pr.height - 8));
    pop.style.left = `${left}px`; pop.style.top = `${top}px`;
  }

  function show(a) {
    const id = decodeURIComponent(hrefOf(a).slice(1));
    const content = buildPreview(id);
    if (!content) return;
    const label = a.textContent.trim() || a.getAttributeNS(XLINK, "title") || id;
    pop.replaceChildren();
    const head = document.createElement("div");
    head.className = "pv-head";
    head.textContent = `预览 · ${label}（单击链接跳转）`;
    pop.append(head, content);
    current = a;
    place(a);
    pop.classList.add("show");
  }
  function hide() { pop.classList.remove("show"); current = null; }

  function setupPreview() {
    pop = document.createElement("div");
    pop.className = "xref-preview";
    pop.setAttribute("role", "tooltip");
    document.body.appendChild(pop);

    document.addEventListener("pointerover", (e) => {
      if (e.pointerType === "touch") return;
      const a = e.target.closest?.("a");
      if (!a || pop.contains(a)) return;                   // 预览框内的链接只负责点击跳转
      if (!hrefOf(a).startsWith("#") || hrefOf(a).length < 2) return;
      clearTimeout(hideTimer);
      if (a === current) return;
      clearTimeout(showTimer);
      showTimer = setTimeout(() => show(a), SHOW_DELAY);
    });
    document.addEventListener("pointerout", (e) => {
      const a = e.target.closest?.("a");
      if (!a || a.contains(e.relatedTarget)) return;      // SVG 链接内各字形间移动不算离开
      clearTimeout(showTimer);
      if (pop.contains(e.relatedTarget)) return;
      hideTimer = setTimeout(hide, HIDE_DELAY);
    });
    pop.addEventListener("pointerenter", () => clearTimeout(hideTimer));
    pop.addEventListener("pointerleave", () => { hideTimer = setTimeout(hide, HIDE_DELAY); });
    document.addEventListener("click", (e) => { if (e.target.closest?.("a")) { clearTimeout(showTimer); hide(); } });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });
    window.addEventListener("scroll", () => { if (current && !pop.matches(":hover")) hide(); }, { passive: true });
  }

  document.addEventListener("DOMContentLoaded", () => { setupResize(); setupBar(); setupPreview(); });
})();
