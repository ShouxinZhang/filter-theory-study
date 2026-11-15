/* 阅读器增强（零外部依赖，离线 build 与在线 serve 共用）：
 *  1. 栏宽：单栏默认自适应，两侧固定手柄可无级拖拽，记忆于 localStorage。
 *  2. 主题：自动 / 浅色 / 深色 三态切换，记忆于 localStorage。
 *  3. 目录单独折叠：文内目录卡片支持整卡折叠与按章收起子节；右上角独立「☰ 目录」浮动抽屉支持筛选与章节滚动高亮（Alt+T）。
 *  4. 链接悬停预览：鼠标悬停页内交叉引用、文献上标或 SVG 内链接时弹出实时目标卡片。
 */
(() => {
  "use strict";
  const root = document.documentElement;
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} },
  };
  const XLINK = "http://www.w3.org/1999/xlink";
  const getDocPane = () => document.getElementById("doc-root") || document.body;

  /* ---------------- 1. 单栏栏宽 ---------------- */
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
        const pane = getDocPane();
        const startX = e.clientX, startW = pane.getBoundingClientRect().width;
        const sign = side === "right" ? 1 : -1;
        document.body.classList.add("resizing");
        const fontPx = parseFloat(getComputedStyle(pane).fontSize) || 17;
        const move = (ev) => {
          const w = Math.max(MIN_PX, Math.min(window.innerWidth, startW + 2 * sign * (ev.clientX - startX)));
          applyMeasure(w);
          badge.textContent = `${Math.round(w)} px · 约 ${Math.round((w - 64) / fontPx)} 字/行`;
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

  /* ---------------- 2. 目录单独折叠（文内卡片 + 浮动抽屉） ---------------- */
  let drawer, drawerBody, drawerFilter, tocBtn;

  function jumpToHeading(id, e) {
    const target = document.getElementById(id);
    if (!target) return;
    target.scrollIntoView({ behavior: "auto", block: "start" });
    target.classList.remove("toc-jumped");
    void target.offsetWidth;
    target.classList.add("toc-jumped");
    if (e && (e.ctrlKey || e.metaKey || e.altKey)) {
      window.dispatchEvent(new CustomEvent("toc:ctrl-jump", { detail: { target } }));
    }
  }

  function wireTocTree(container) {
    if (!container) return;
    if (!container.dataset.itemWired) {
      container.dataset.itemWired = "1";
      container.addEventListener("click", (e) => {
        const item = e.target.closest?.(".toc-item[data-target]");
        if (!item || !container.contains(item)) return;
        e.preventDefault();
        e.stopPropagation();
        jumpToHeading(item.dataset.target, e);
        if (container.closest(".toc-drawer") && window.innerWidth < 920) toggleDrawer(false);
      });
    }
    container.querySelectorAll(".toc-caret").forEach((btn) => {
      if (btn.dataset.wired) return;
      btn.dataset.wired = "1";
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const li = btn.closest("li.toc-branch");
        if (!li) return;
        const folded = li.classList.toggle("is-folded");
        btn.setAttribute("aria-expanded", String(!folded));
      });
    });
    container.querySelectorAll("[data-toc-act]").forEach((btn) => {
      if (btn.dataset.wired) return;
      btn.dataset.wired = "1";
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const scope = btn.closest("nav.toc, .toc-drawer") || container;
        const fold = btn.dataset.tocAct === "fold-sub";
        scope.querySelectorAll("li.toc-branch").forEach((li) => {
          li.classList.toggle("is-folded", fold);
          const c = li.querySelector(":scope > .toc-row > .toc-caret");
          if (c) c.setAttribute("aria-expanded", String(!fold));
        });
      });
    });
  }

  function bindInlineToc() {
    const nav = document.querySelector("nav.toc");
    if (!nav) return;
    // 兼容并改造遗留静态超链接目录项为无超链接大纲按钮
    nav.querySelectorAll('a[href^="#"]').forEach((a) => {
      const id = decodeURIComponent(a.getAttribute("href").slice(1));
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "toc-item";
      btn.dataset.target = id;
      btn.append(...Array.from(a.childNodes));
      a.replaceWith(btn);
    });
    // 兼容未带 .toc-head 的旧版静态目录结构
    if (!nav.querySelector(".toc-head")) {
      const ol = nav.querySelector("ol");
      const count = nav.querySelectorAll(".toc-item").length;
      const head = document.createElement("div");
      head.className = "toc-head";
      head.innerHTML = `<button type="button" class="toc-toggle" aria-expanded="true" title="点击折叠或展开目录卡片">`
        + `<span class="toc-toggle-icon">▾</span><strong>目录</strong><span class="toc-meta">共 ${count} 节</span></button>`;
      const bodyWrap = document.createElement("div");
      bodyWrap.className = "toc-body";
      if (ol) bodyWrap.appendChild(ol);
      nav.replaceChildren(head, bodyWrap);
    }
    const toggle = nav.querySelector(".toc-toggle");
    const savedCollapsed = store.get("reader.tocCollapsed") === "1";
    nav.classList.toggle("is-collapsed", savedCollapsed);
    if (toggle) {
      toggle.setAttribute("aria-expanded", String(!savedCollapsed));
      if (!toggle.dataset.wired) {
        toggle.dataset.wired = "1";
        toggle.addEventListener("click", () => {
          const collapsed = nav.classList.toggle("is-collapsed");
          toggle.setAttribute("aria-expanded", String(!collapsed));
          store.set("reader.tocCollapsed", collapsed ? "1" : "0");
        });
      }
    }
    wireTocTree(nav);
  }

  function collectHeadingsTree() {
    const pane = getDocPane();
    const heads = Array.from(pane.querySelectorAll("h2[id], h3[id], h4[id]"));
    const roots = [], stack = [];
    for (const h of heads) {
      const lv = h.tagName === "H2" ? 1 : h.tagName === "H3" ? 2 : 3;
      const numEl = h.querySelector(".secnum");
      const num = numEl ? numEl.textContent.trim() : "";
      const clone = h.cloneNode(true);
      clone.querySelector(".secnum")?.remove();
      const title = clone.textContent.trim();
      const node = { lv, id: h.id, num, title, children: [] };
      while (stack.length && stack[stack.length - 1].lv >= lv) stack.pop();
      if (stack.length) stack[stack.length - 1].children.push(node);
      else roots.push(node);
      stack.push(node);
    }
    return { roots, total: heads.length };
  }

  function renderDrawerTree() {
    if (!drawerBody) return;
    const { roots, total } = collectHeadingsTree();
    if (tocBtn) tocBtn.style.display = total ? "" : "none";
    const q = (drawerFilter?.value || "").trim().toLowerCase();

    function emit(items) {
      const ol = document.createElement("ol");
      for (const n of items) {
        const selfHit = !q || `${n.num} ${n.title}`.toLowerCase().includes(q);
        const childOl = n.children.length ? emit(n.children) : null;
        const hasChildHit = childOl && childOl.children.length > 0;
        if (!selfHit && !hasChildHit) continue;

        const li = document.createElement("li");
        li.className = n.children.length ? "toc-branch" : "toc-leaf";
        li.dataset.lv = String(n.lv);
        const row = document.createElement("div");
        row.className = "toc-row";
        row.dataset.targetId = n.id;

        if (n.children.length) {
          const caret = document.createElement("button");
          caret.type = "button";
          caret.className = "toc-caret";
          caret.textContent = "▾";
          caret.title = "折叠或展开子节";
          caret.setAttribute("aria-expanded", "true");
          row.appendChild(caret);
        } else {
          const pad = document.createElement("span");
          pad.className = "toc-caret-pad";
          row.appendChild(pad);
        }

        const item = document.createElement("button");
        item.type = "button";
        item.className = "toc-item";
        item.dataset.target = n.id;
        const numSpan = document.createElement("span");
        numSpan.className = "toc-num";
        numSpan.textContent = n.num;
        const txtSpan = document.createElement("span");
        txtSpan.className = "toc-txt";
        txtSpan.textContent = n.title;
        item.append(numSpan, txtSpan);
        row.appendChild(item);
        li.appendChild(row);
        if (childOl && childOl.children.length) li.appendChild(childOl);
        ol.appendChild(li);
      }
      return ol;
    }

    drawerBody.replaceChildren(emit(roots));
    wireTocTree(drawer);
    updateScrollSpy();
  }

  function updateScrollSpy() {
    if (!drawer || !drawer.classList.contains("open")) return;
    const pane = getDocPane();
    const heads = Array.from(pane.querySelectorAll("h2[id], h3[id], h4[id]"));
    if (!heads.length) return;
    let activeId = heads[0].id;
    const threshold = 110;
    for (const h of heads) {
      if (h.getBoundingClientRect().top <= threshold) activeId = h.id;
      else break;
    }
    drawer.querySelectorAll(".toc-row.is-current").forEach((r) => r.classList.remove("is-current"));
    const cur = drawer.querySelector(`.toc-row[data-target-id="${CSS.escape(activeId)}"]`);
    if (cur) cur.classList.add("is-current");
  }

  function toggleDrawer(force) {
    if (!drawer) return;
    const next = typeof force === "boolean" ? force : !drawer.classList.contains("open");
    drawer.classList.toggle("open", next);
    if (tocBtn) tocBtn.classList.toggle("is-active", next);
    if (next) {
      renderDrawerTree();
      setTimeout(() => drawerFilter?.focus(), 20);
    }
  }

  function setupTocDrawer() {
    drawer = document.createElement("aside");
    drawer.className = "toc-drawer";
    drawer.setAttribute("aria-label", "浮动章节目录");
    drawer.innerHTML = `<div class="toc-drawer-head">`
      + `<input type="search" class="toc-drawer-filter" placeholder="筛选章节标题…">`
      + `<button type="button" class="toc-sub-btn" data-toc-act="fold-sub" title="仅显示一级章">章</button>`
      + `<button type="button" class="toc-sub-btn" data-toc-act="expand-all" title="展开全部小节">全</button>`
      + `</div><div class="toc-drawer-body"></div>`;
    document.body.appendChild(drawer);
    drawerBody = drawer.querySelector(".toc-drawer-body");
    drawerFilter = drawer.querySelector(".toc-drawer-filter");
    drawerFilter.addEventListener("input", renderDrawerTree);
    drawerFilter.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (drawerFilter.value) { drawerFilter.value = ""; renderDrawerTree(); }
        else toggleDrawer(false);
      }
    });
    wireTocTree(drawer);

    const onScroll = () => updateScrollSpy();
    window.addEventListener("scroll", onScroll, { passive: true });
    getDocPane().addEventListener("scroll", onScroll, { passive: true });
    document.addEventListener("mousedown", (e) => {
      if (drawer.classList.contains("open") && !drawer.contains(e.target) && !tocBtn?.contains(e.target)) {
        toggleDrawer(false);
      }
    });
  }

  /* ---------------- 3. 主题与右上角工具条（单色线性 SVG 图标） ---------------- */
  const ico = (d) =>
    `<svg class="cc-ico" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const SVG_TOC = ico('<path d="M2.5 4h11M2.5 8h8M2.5 12h11"/>');
  const SVG_MEASURE = ico('<path d="M2 8h12M4.5 5.5 2 8l2.5 2.5M11.5 5.5 14 8l-2.5 2.5"/>');
  const THEMES = ["auto", "light", "dark"];
  const THEME_LABEL = {
    auto: `${ico('<circle cx="8" cy="8" r="5.5"/><path d="M8 2.5v11a5.5 5.5 0 0 0 0-11z" fill="currentColor" stroke="none"/>')}<span>自动</span>`,
    light: `${ico('<circle cx="8" cy="8" r="3"/><path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1.1 1.1M11.5 11.5l1.1 1.1M12.6 3.4l-1.1 1.1M4.5 11.5l-1.1 1.1"/>')}<span>浅色</span>`,
    dark: `${ico('<path d="M13 9.8A5.5 5.5 0 0 1 6.2 3 5.5 5.5 0 1 0 13 9.8Z"/>')}<span>深色</span>`,
  };
  const applyTheme = (t) => { t === "auto" ? root.removeAttribute("data-theme") : root.setAttribute("data-theme", t); };
  let theme = THEMES.includes(store.get("reader.theme")) ? store.get("reader.theme") : "auto";
  applyTheme(theme);

  function setupBar() {
    const bar = document.createElement("div");
    bar.className = "reader-bar";
    bar.id = "reader-bar";

    tocBtn = document.createElement("button");
    tocBtn.type = "button";
    tocBtn.dataset.role = "toc";
    tocBtn.innerHTML = `${SVG_TOC}<span>目录</span>`;
    tocBtn.title = "展开或收起浮动章节目录（快捷键 Alt+T）";
    tocBtn.onclick = () => toggleDrawer();

    const tBtn = document.createElement("button");
    tBtn.type = "button";
    tBtn.dataset.role = "theme";
    tBtn.innerHTML = THEME_LABEL[theme];
    tBtn.title = "切换主题：自动（跟随系统）/ 浅色 / 深色";
    tBtn.onclick = () => {
      theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
      applyTheme(theme); store.set("reader.theme", theme); tBtn.innerHTML = THEME_LABEL[theme];
    };

    const wBtn = document.createElement("button");
    wBtn.type = "button";
    wBtn.dataset.role = "measure";
    wBtn.innerHTML = `${SVG_MEASURE}<span>宽度</span>`;
    wBtn.title = "恢复自适应栏宽（也可拖拽正文两侧边缘调整）";
    wBtn.onclick = resetMeasure;

    bar.append(tocBtn, tBtn, wBtn);
    document.body.appendChild(bar);
  }

  /* ---------------- 4. 链接悬停预览 ---------------- */
  const SHOW_DELAY = 280, HIDE_DELAY = 220;
  let pop, showTimer, hideTimer, current;

  const hrefOf = (a) => a.getAttribute("href") || a.getAttributeNS(XLINK, "href") || "";
  const isHeading = (el) => /^H[1-6]$/.test(el.tagName);

  function buildPreview(id) {
    const target = document.getElementById(id);
    if (!target) return null;
    const nodes = [target];
    if (isHeading(target)) {
      let n = target.nextElementSibling;
      while (n && nodes.length < 3 && !isHeading(n)) { nodes.push(n); n = n.nextElementSibling; }
    } else if (target.matches("div.thm") && target.nextElementSibling?.matches("div.proof")) {
      nodes.push(target.nextElementSibling);
    }
    const box = document.createElement("div");
    for (const n of nodes) {
      const c = n.cloneNode(true);
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
    const left = Math.min(Math.max(8, r.left + r.width / 2 - pr.width / 2), vw - pr.width - 8);
    let top = r.bottom + gap;
    if (top + pr.height > vh - 8 && r.top - gap - pr.height > 8) top = r.top - gap - pr.height;
    top = Math.max(8, Math.min(top, vh - pr.height - 8));
    pop.style.left = `${left}px`; pop.style.top = `${top}px`;
  }

  function show(a) {
    if (root.classList.contains("ctrl-aiming")) return;
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
  function hide() { if (pop) pop.classList.remove("show"); current = null; }

  function setupPreview() {
    pop = document.createElement("div");
    pop.className = "xref-preview";
    pop.setAttribute("role", "tooltip");
    document.body.appendChild(pop);

    document.addEventListener("pointerover", (e) => {
      if (e.pointerType === "touch" || e.ctrlKey || e.metaKey) return;
      const a = e.target.closest?.("a");
      if (!a || pop.contains(a) || a.closest("nav.toc, .toc-drawer")) return;
      if (!hrefOf(a).startsWith("#") || hrefOf(a).length < 2) return;
      clearTimeout(hideTimer);
      if (a === current) return;
      clearTimeout(showTimer);
      showTimer = setTimeout(() => show(a), SHOW_DELAY);
    });
    document.addEventListener("pointerout", (e) => {
      const a = e.target.closest?.("a");
      if (!a || a.contains(e.relatedTarget)) return;
      clearTimeout(showTimer);
      if (pop.contains(e.relatedTarget)) return;
      hideTimer = setTimeout(hide, HIDE_DELAY);
    });
    pop.addEventListener("pointerenter", () => clearTimeout(hideTimer));
    pop.addEventListener("pointerleave", () => { hideTimer = setTimeout(hide, HIDE_DELAY); });
    document.addEventListener("click", (e) => {
      const a = e.target.closest?.("a");
      if (!a) return;
      clearTimeout(showTimer); hide();
      // 双栏模式下 #doc-root 是独立滚动容器，页内锚点用 scrollIntoView 平滑跳转
      const href = hrefOf(a);
      if (href.startsWith("#") && href.length > 1 && !(e.ctrlKey || e.metaKey)) {
        const id = decodeURIComponent(href.slice(1));
        const target = document.getElementById(id);
        if (target && getDocPane().contains(target)) {
          e.preventDefault();
          target.scrollIntoView({ behavior: "auto", block: "start" });
          history.replaceState(null, "", `#${id}`);
        }
      }
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") hide();
      if (e.altKey && !e.ctrlKey && !e.metaKey && e.code === "KeyT") {
        e.preventDefault();
        toggleDrawer();
      }
    });
    const onScrollHide = () => { if (current && !pop.matches(":hover")) hide(); };
    window.addEventListener("scroll", onScrollHide, { passive: true });
    getDocPane().addEventListener("scroll", onScrollHide, { passive: true });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupResize();
    setupBar();
    setupTocDrawer();
    bindInlineToc();
    const { total } = collectHeadingsTree();
    if (tocBtn) tocBtn.style.display = total ? "" : "none";
    setupPreview();
  });

  window.addEventListener("doc:patched", () => {
    bindInlineToc();
    if (drawer?.classList.contains("open")) renderDrawerTree();
    else {
      const { total } = collectHeadingsTree();
      if (tocBtn) tocBtn.style.display = total ? "" : "none";
    }
  });
})();
