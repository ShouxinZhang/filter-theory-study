/* 多论文工作区外壳：左上常驻 Home 键零延迟显隐 210px 侧边栏 + 新建弹层 + visibility 叠放切换 + MAX_ALIVE=3 LRU 池 */
(() => {
  "use strict";
  const root = document.documentElement;
  const { api, escHtml, ico } = window.HTD;
  const MAX_ALIVE = 3;
  const KEY_ORDER = "htd:shell:order", KEY_ACTIVE = "htd:shell:active", KEY_RECENT = "htd:shell:recent", KEY_SIDE = "htd:shell:sidebarOpen";
  const SVG_HOME = ico('<path d="M2.2 7.4 8 2.5l5.8 4.9M3.8 6.4v6.6h3.1V9.6h2.2V13h3.1V6.4"/>', 16);
  const SVG_PLUS = ico('<path d="M8 3v10M3 8h10"/>', 14);
  const SVG_DOC = ico('<path d="M4 2.2h5.4L12.5 5.3v8.5H4z"/><path d="M9.2 2.2v3.3h3.3"/>', 13);

  const getLS = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
  const setLS = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} };
  const getJSON = (k, fb) => { try { return JSON.parse(getLS(k) || "null") ?? fb; } catch { return fb; } };
  const setJSON = (k, v) => setLS(k, JSON.stringify(v));
  const getScroll = (id) => { try { return JSON.parse(sessionStorage.getItem(`htd:shell:scroll:${id}`) || "null"); } catch { return null; } };
  const setScroll = (id, pos) => { try { sessionStorage.setItem(`htd:shell:scroll:${id}`, JSON.stringify(pos)); } catch {} };

  const applyTheme = () => { const t = getLS("reader.theme"); t === "light" || t === "dark" ? root.setAttribute("data-theme", t) : root.removeAttribute("data-theme"); };
  applyTheme();
  window.addEventListener("storage", (e) => { if (!e.key || e.key === "reader.theme") applyTheme(); });

  let libraryName = "", papers = [], order = [], byId = new Map();
  let sideOpen = getLS(KEY_SIDE) !== "0", activeId = "", clock = 0, dragId = "", creating = false;
  const frames = new Map();
  let appEl, toggleBtn, railEl, libNameEl, libCntEl, newBtn, tabsEl, stageEl, loadingEl, emptyEl, tipEl, popEl, nameIn, titleIn, errEl, submitBtn;

  function applyOrder(rawList) {
    const map = new Map(rawList.map((p) => [p.id, p])), saved = getJSON(KEY_ORDER, []);
    order = Array.isArray(saved) ? saved.filter((id) => map.has(id)) : [];
    for (const p of rawList) if (!order.includes(p.id)) order.push(p.id);
    setJSON(KEY_ORDER, order);
    papers = order.map((id) => map.get(id));
    byId = new Map(papers.map((p) => [p.id, p]));
  }

  function showTip(anchor, title, sub = "") {
    if (!tipEl || !sideOpen || popEl?.classList.contains("is-open")) return;
    tipEl.innerHTML = `<div class="sh-tip-title">${escHtml(title)}</div>` + (sub ? `<div class="sh-tip-sub ui-hint">${escHtml(sub)}</div>` : "");
    tipEl.classList.add("is-open");
    const r = anchor.getBoundingClientRect();
    tipEl.style.top = `${Math.round(Math.max(6, Math.min(window.innerHeight - tipEl.offsetHeight - 6, r.top + (r.height - tipEl.offsetHeight) / 2)))}px`;
  }
  const hideTip = () => tipEl?.classList.remove("is-open");
  const closeCreatePop = () => popEl?.classList.remove("is-open");

  function setSidebarOpen(open, refresh = true) {
    sideOpen = Boolean(open);
    railEl?.classList.toggle("is-collapsed", !sideOpen);
    toggleBtn?.classList.toggle("is-open", sideOpen);
    toggleBtn?.setAttribute("aria-expanded", String(sideOpen));
    setLS(KEY_SIDE, sideOpen ? "1" : "0");
    if (!sideOpen) { hideTip(); closeCreatePop(); }
    else if (refresh) refreshPapersQuiet();
  }

  function syncRailState() {
    if (libNameEl) libNameEl.textContent = libraryName || "论文工作区";
    if (libCntEl) libCntEl.textContent = `${frames.size}/${MAX_ALIVE}`;
    tabsEl?.querySelectorAll(".sh-tab").forEach((b) => {
      const id = b.dataset.id, on = id === activeId;
      b.classList.toggle("is-current", on); b.classList.toggle("is-alive", frames.has(id)); b.setAttribute("aria-selected", String(on));
    });
    emptyEl?.classList.toggle("is-active", !papers.length);
  }

  function renderRail() {
    if (!tabsEl) return;
    tabsEl.innerHTML = papers.map((p) => {
      const sub = p.entry ? `${p.id} · ${p.entry}` : p.id;
      return `<button type="button" role="tab" draggable="true" class="sh-tab ui-row" data-id="${escHtml(p.id)}" data-tip="${escHtml(p.title)}" data-sub="${escHtml(sub)}" aria-label="${escHtml(p.title)}">${SVG_DOC}<span class="sh-tab-title">${escHtml(p.title)}</span><span class="sh-dot"></span></button>`;
    }).join("");
    syncRailState();
  }

  function saveFrameScroll(id, rec) {
    try {
      const win = rec.el.contentWindow, doc = rec.el.contentDocument;
      if (win && doc) setScroll(id, { winY: Math.round(win.scrollY || doc.documentElement?.scrollTop || 0), docTop: Math.round(doc.getElementById("doc-root")?.scrollTop || 0), edTop: Math.round(doc.querySelector(".ed-scroll")?.scrollTop || 0) });
    } catch {}
  }

  function bindFrameHotkeys(iframe) {
    try {
      iframe.contentWindow?.addEventListener("keydown", (e) => {
        if (e.altKey && (e.key === "b" || e.key === "B")) { e.preventDefault(); setSidebarOpen(!sideOpen); }
      });
    } catch {}
  }

  function ensureFrame(id) {
    if (frames.has(id)) return frames.get(id);
    const p = byId.get(id);
    if (!p) return null;
    while (frames.size >= MAX_ALIVE) {
      const cands = [...frames.entries()].filter(([k]) => k !== id);
      if (!cands.length) break;
      cands.sort((a, b) => (a[0] === activeId) - (b[0] === activeId) || a[1].lastUsed - b[1].lastUsed);
      const [vid, vrec] = cands[0];
      saveFrameScroll(vid, vrec); vrec.el.remove(); frames.delete(vid);
    }
    const iframe = Object.assign(document.createElement("iframe"), { className: "sh-frame", src: p.url });
    iframe.dataset.id = id;
    const rec = { el: iframe, loaded: false, lastUsed: ++clock, onReady: [] };
    frames.set(id, rec); stageEl.appendChild(iframe); syncRailState();
    iframe.addEventListener("load", () => {
      rec.loaded = true;
      bindFrameHotkeys(iframe);
      if (activeId === id) loadingEl.classList.remove("is-active");
      const saved = getScroll(id);
      if (saved) {
        const restore = () => {
          try {
            const win = iframe.contentWindow, doc = iframe.contentDocument;
            if (saved.winY > 0) win?.scrollTo(0, saved.winY);
            if (saved.docTop > 0 && doc?.getElementById("doc-root")) doc.getElementById("doc-root").scrollTop = saved.docTop;
            if (saved.edTop > 0 && doc?.querySelector(".ed-scroll")) doc.querySelector(".ed-scroll").scrollTop = saved.edTop;
          } catch {}
        };
        restore(); requestAnimationFrame(restore);
      }
      while (rec.onReady.length) rec.onReady.shift()();
    });
    return rec;
  }

  function activatePaper(id) {
    const p = byId.get(id);
    if (!p) return;
    activeId = id;
    const rec = ensureFrame(id);
    rec.lastUsed = ++clock;
    for (const [fid, r] of frames) r.el.classList.toggle("is-active", fid === id);
    loadingEl.classList.toggle("is-active", !rec.loaded); syncRailState();
    const prev = getJSON(KEY_RECENT, []);
    setJSON(KEY_RECENT, [id, ...(Array.isArray(prev) ? prev.filter((x) => x !== id) : [])].slice(0, 12));
    setLS(KEY_ACTIVE, id); document.title = `${p.title} — ${libraryName || "论文工作区"}`;
  }

  async function refreshPapersQuiet() {
    try {
      const r = await fetch(api("__api/papers"), { cache: "no-store" });
      if (!r.ok) return;
      const d = await r.json();
      libraryName = d.library || libraryName; applyOrder(d.papers || []); renderRail();
      if (papers.length && (!activeId || !byId.has(activeId))) activatePaper(papers[0].id);
    } catch {}
  }

  function openCreatePop(fromEmpty = false) {
    hideTip(); errEl.hidden = true; errEl.textContent = "";
    if (!sideOpen && !fromEmpty) setSidebarOpen(true, false);
    popEl.style.left = fromEmpty ? "50%" : "8px";
    popEl.style.top = fromEmpty ? "42%" : `${Math.round((newBtn?.getBoundingClientRect().bottom || 78) + 6)}px`;
    popEl.style.transform = fromEmpty ? "translate(-50%, -50%)" : "none";
    popEl.classList.add("is-open"); nameIn.focus();
  }

  function schedulePrewarm(excludeId) {
    setTimeout(() => {
      const run = () => {
        const recent = getJSON(KEY_RECENT, []);
        const cand = (Array.isArray(recent) ? recent : []).find((id) => id !== excludeId && id !== activeId && byId.has(id) && !frames.has(id));
        if (cand && frames.size < MAX_ALIVE) { const rec = ensureFrame(cand); if (rec) rec.lastUsed = 0; }
      };
      window.requestIdleCallback ? requestIdleCallback(run, { timeout: 200 }) : run();
    }, 800);
  }

  async function boot() {
    appEl = document.getElementById("sh-app");
    if (!appEl) return;
    appEl.innerHTML = `<button type="button" id="sh-toggle" class="sh-toggle ui-btn" title="显示 / 隐藏论文栏 (Alt+B)" aria-label="显示或隐藏论文侧边栏">${SVG_HOME}</button><aside class="sh-rail" aria-label="论文垂直标签栏"><div class="sh-head"><span class="sh-lib-name"></span><span class="sh-lib-cnt ui-hint" title="内存已驻留 / 上限"></span></div><button type="button" class="sh-new-row ui-row" data-role="add">${SVG_PLUS}<span>新建论文</span></button><div class="ui-sep sh-rail-sep"></div><div class="sh-tabs" role="tablist"></div></aside><main class="sh-stage"><div id="sh-loading" class="sh-loading ui-hint">正在加载论文…</div><div id="sh-empty" class="sh-empty-wrap"><span class="ui-hint">当前论文库尚无工程</span><button type="button" class="sh-empty-btn ui-btn" data-role="empty-add">${SVG_PLUS}<span>新建第一篇论文</span></button></div></main>`;
    document.body.insertAdjacentHTML("beforeend", `<div id="sh-tip" class="sh-tip ui-popover" role="tooltip"></div><form id="sh-create-pop" class="sh-pop ui-popover"><div class="sh-pop-title">新建论文工作区</div><input class="sh-input ui-input" name="name" placeholder="目录名（如 kalman-note）" autocomplete="off"><input class="sh-input ui-input" name="title" placeholder="论文标题（可选）" autocomplete="off"><div class="sh-err ui-hint" hidden></div><div class="sh-pop-foot"><button type="button" class="ui-btn ui-btn--sm" data-act="cancel">取消</button><button type="submit" class="ui-btn ui-btn--sm is-active" data-act="submit">创建</button></div></form>`);

    toggleBtn = document.getElementById("sh-toggle"); railEl = appEl.querySelector(".sh-rail"); libNameEl = appEl.querySelector(".sh-lib-name"); libCntEl = appEl.querySelector(".sh-lib-cnt");
    newBtn = appEl.querySelector('[data-role="add"]'); tabsEl = appEl.querySelector(".sh-tabs"); stageEl = appEl.querySelector(".sh-stage");
    loadingEl = document.getElementById("sh-loading"); emptyEl = document.getElementById("sh-empty"); tipEl = document.getElementById("sh-tip"); popEl = document.getElementById("sh-create-pop");
    nameIn = popEl.elements.name; titleIn = popEl.elements.title; errEl = popEl.querySelector(".sh-err"); submitBtn = popEl.querySelector('[data-act="submit"]');

    setSidebarOpen(sideOpen, false);
    toggleBtn.onclick = () => setSidebarOpen(!sideOpen);
    newBtn.onclick = (e) => { e.stopPropagation(); popEl.classList.contains("is-open") ? closeCreatePop() : openCreatePop(false); };
    emptyEl.querySelector('[data-role="empty-add"]').onclick = (e) => { e.stopPropagation(); openCreatePop(true); };

    railEl.addEventListener("pointerover", (e) => { const b = e.target.closest?.("[data-tip]"); if (b) showTip(b, b.dataset.tip, b.dataset.sub); });
    railEl.addEventListener("pointerout", (e) => { if (!e.relatedTarget || !e.target.closest?.("[data-tip]")?.contains(e.relatedTarget)) hideTip(); });
    tabsEl.addEventListener("scroll", hideTip, { passive: true });
    tabsEl.addEventListener("click", (e) => { const b = e.target.closest?.(".sh-tab[data-id]"); if (b) { hideTip(); closeCreatePop(); activatePaper(b.dataset.id); } });
    tabsEl.addEventListener("dragstart", (e) => { const b = e.target.closest?.(".sh-tab[data-id]"); if (b) { dragId = b.dataset.id; e.dataTransfer.effectAllowed = "move"; hideTip(); } });
    tabsEl.addEventListener("dragend", () => { dragId = ""; });
    tabsEl.addEventListener("dragover", (e) => { const b = e.target.closest?.(".sh-tab[data-id]"); if (b && dragId && dragId !== b.dataset.id) e.preventDefault(); });
    tabsEl.addEventListener("drop", (e) => {
      const b = e.target.closest?.(".sh-tab[data-id]"), from = order.indexOf(dragId), to = b ? order.indexOf(b.dataset.id) : -1;
      if (!b || !dragId || dragId === b.dataset.id || from < 0 || to < 0) return;
      e.preventDefault(); order.splice(from, 1); order.splice(to, 0, dragId);
      setJSON(KEY_ORDER, order); papers = order.map((id) => byId.get(id)).filter(Boolean);
      renderRail();
    });

    popEl.querySelector('[data-act="cancel"]').onclick = closeCreatePop;
    document.addEventListener("mousedown", (e) => { if (popEl.classList.contains("is-open") && !popEl.contains(e.target) && !newBtn.contains(e.target) && !e.target.closest?.('[data-role="empty-add"]')) closeCreatePop(); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeCreatePop();
      else if (e.altKey && (e.key === "b" || e.key === "B")) { e.preventDefault(); setSidebarOpen(!sideOpen); }
    });

    popEl.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (creating) return;
      const name = nameIn.value.trim(), title = titleIn.value.trim();
      if (!name) { errEl.textContent = "请输入新论文目录名"; errEl.hidden = false; nameIn.focus(); return; }
      creating = true; submitBtn.disabled = true; submitBtn.textContent = "创建中…"; errEl.hidden = true;
      try {
        const r = await fetch(api("__api/papers"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(title ? { name, title } : { name }) });
        const d = await r.json();
        if (!r.ok || !d.paper) { errEl.textContent = d.error || `创建失败 (${r.status})`; errEl.hidden = false; return; }
        const np = d.paper;
        if (!order.includes(np.id)) { order.push(np.id); setJSON(KEY_ORDER, order); }
        byId.set(np.id, np); papers = order.map((id) => byId.get(id)).filter(Boolean);
        renderRail(); nameIn.value = ""; titleIn.value = ""; closeCreatePop(); activatePaper(np.id);
      } catch (err) { errEl.textContent = `请求出错：${err.message || err}`; errEl.hidden = false; }
      finally { creating = false; submitBtn.disabled = false; submitBtn.textContent = "创建"; }
    });

    try {
      const r = await fetch(api("__api/papers"), { cache: "no-store" });
      const d = await r.json();
      libraryName = d.library || ""; applyOrder(d.papers || []);
    } catch {}
    renderRail();

    if (papers.length) {
      const saved = getLS(KEY_ACTIVE), recent = getJSON(KEY_RECENT, []);
      const firstId = byId.has(saved) ? saved : ((Array.isArray(recent) && recent.find((id) => byId.has(id))) || papers[0].id);
      activatePaper(firstId);
      const rec = frames.get(firstId);
      if (rec) rec.loaded ? schedulePrewarm(firstId) : rec.onReady.push(() => schedulePrewarm(firstId));
    }
  }

  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", boot) : boot();
})();
