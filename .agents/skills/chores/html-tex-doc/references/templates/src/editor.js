/* Web 双栏源码工作台 + 全文搜索 + 类 LaTeX Workshop SyncTeX 正反向行级高亮对齐（仅 serve 模式加载）：
 *  - 快捷键：
 *      Ctrl+\          开启 / 收起双栏工作台
 *      Ctrl+S          立即保存当前文件并触发局部渲染
 *      Ctrl+F          当前文件内搜索（Enter / Shift+Enter 上下跳转）
 *      Ctrl+Shift+F    跨全部源文件全局搜索
 *      Ctrl+单击(右侧) / Alt+单击(右侧)   反向同步：从渲染文字/公式/图表精准跳回左侧源码行与词语位置
 *      Ctrl+单击(左侧) / 单击行号槽 / Ctrl+Alt+J / Alt+Enter   正向同步：从源码行跳至右侧对应渲染行高亮
 *      按住 Ctrl 悬停右侧                 实时瞄准框与源文件行号角标预览
 */
(() => {
  "use strict";
  if (!window.__HTML_TEX_LIVE__) return;

  const root = document.documentElement;
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} },
  };
  const escHtml = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const escRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  let docRoot, splitBtn, edPane, resizer, fileSelect, dirtyDot;
  let findBar, findInput, findCountEl, caseBtn, regexBtn, globalBox;
  let autoSaveBtn, linkSyncBtn, statusLeft, statusRight;
  let edScroll, edStage, edBackdrop, edTa;
  let aimBadge, errBanner;

  // 编辑器状态
  let filesMeta = [];
  let curFile = "";
  let baseMtime = null;
  let diskContent = "";
  let isDirty = false;
  let isSplit = store.get("editor.splitOpen") === "1";
  let autoSave = store.get("editor.autoSave") !== "0";
  let linkSync = store.get("editor.linkSync") !== "0";
  let curLine = 1;
  let syncRange = null; // { l1, l2 }
  let findState = { q: "", cs: false, rx: false, hits: [], idx: -1 };
  let autoSaveTimer = null;
  let peerTimer = null;
  let hlClearTimer = null;

  /* ---------------- 1. 右侧 #doc-root 块级无闪烁热刷新 ---------------- */
  let liveVer = -1, rawChildren = [], liveReady = false;

  const parseHtmlChildren = (htmlText) =>
    Array.from(new DOMParser().parseFromString(htmlText, "text/html").body.children).map((e) => e.outerHTML);

  async function fetchRawChildren() {
    const res = await fetch("/__raw", { cache: "no-store" });
    return parseHtmlChildren(await res.text());
  }

  function showErrBanner(msg) {
    if (!errBanner) {
      errBanner = document.createElement("pre");
      errBanner.className = "live-err";
      document.body.appendChild(errBanner);
    }
    errBanner.textContent = msg || "";
    errBanner.style.display = msg ? "block" : "none";
  }

  function makeNodes(htmlList) {
    const tpl = document.createElement("template");
    tpl.innerHTML = htmlList.join("");
    return Array.from(tpl.content.children);
  }

  async function patchDocRoot(fromExternal) {
    if (!docRoot) return;
    const next = await fetchRawChildren();
    const curNodes = Array.from(docRoot.children);
    if (rawChildren.length !== curNodes.length) {
      docRoot.innerHTML = next.join("");
      rawChildren = next;
      if (window.MathJax?.typesetPromise) await MathJax.typesetPromise([docRoot]);
      window.dispatchEvent(new CustomEvent("doc:patched"));
      if (isSplit && linkSync) updatePeerIndicator(false);
      return;
    }

    const added = [], gone = [];
    const isToc = (h) => h.startsWith('<nav class="toc"');
    const tOld = rawChildren.findIndex(isToc), tNew = next.findIndex(isToc);
    if (tOld >= 0 && tOld === tNew && rawChildren[tOld] !== next[tNew]) {
      const wasCollapsed = curNodes[tOld].classList.contains("is-collapsed");
      const n = makeNodes([next[tNew]])[0];
      if (wasCollapsed) n.classList.add("is-collapsed");
      curNodes[tOld].replaceWith(n);
      curNodes[tOld] = n;
      rawChildren[tOld] = next[tNew];
    }

    let p = 0;
    while (p < rawChildren.length && p < next.length && rawChildren[p] === next[p]) p++;
    let s = 0;
    while (
      s < rawChildren.length - p &&
      s < next.length - p &&
      rawChildren[rawChildren.length - 1 - s] === next[next.length - 1 - s]
    ) s++;

    const oldMid = curNodes.slice(p, curNodes.length - s);
    const newMid = next.slice(p, next.length - s);
    const tailAnchor = curNodes[curNodes.length - s] || null;

    if (oldMid.length === newMid.length) {
      oldMid.forEach((node, i) => {
        if (rawChildren[p + i] === newMid[i]) return;
        const m = makeNodes([newMid[i]])[0];
        node.replaceWith(m);
        gone.push(node);
        added.push(m);
      });
    } else {
      const fresh = makeNodes(newMid);
      oldMid.forEach((n) => { n.remove(); gone.push(n); });
      fresh.forEach((n) => { docRoot.insertBefore(n, tailAnchor); added.push(n); });
    }
    rawChildren = next;

    if (added.length) {
      window.MathJax?.typesetClear?.(gone);
      if (window.MathJax?.typesetPromise) await MathJax.typesetPromise(added);
      if (fromExternal && !isSplit) {
        const r = added[0].getBoundingClientRect();
        if (r.bottom < 0 || r.top > window.innerHeight) added[0].scrollIntoView({ behavior: "smooth", block: "center" });
      }
      added.forEach((n) => n.classList.add("live-new"));
      setTimeout(() => added.forEach((n) => n.classList.remove("live-new")), 1400);
    }
    window.dispatchEvent(new CustomEvent("doc:patched"));
    if (isSplit && linkSync) updatePeerIndicator(false);
  }

  let lastSelfSavedMtime = 0;

  async function liveLoop() {
    for (;;) {
      try {
        const res = await fetch(`/__live?v=${liveVer}`, { cache: "no-store" });
        const data = await res.json();
        if (data.v === liveVer) continue;
        const isFirst = liveVer < 0;
        liveVer = data.v;
        showErrBanner(data.err);
        if (isFirst) continue;

        // 若外部编辑器修改了当前打开的文件，且本地无未保存改动，自动热同步左侧原文
        if (isSplit && curFile && Array.isArray(data.changed) && data.changed.includes(curFile)) {
          await syncExternalFileIfClean();
        }

        if (!data.err) {
          if (liveReady) await patchDocRoot(!isSplit);
          else location.reload();
        }
      } catch {
        await new Promise((r) => setTimeout(r, 1000));
      }
    }
  }

  async function syncExternalFileIfClean() {
    try {
      const r = await fetch(`/__api/file?path=${encodeURIComponent(curFile)}`, { cache: "no-store" });
      if (!r.ok) return;
      const d = await r.json();
      if (d.mtime_ns === baseMtime || d.mtime_ns === lastSelfSavedMtime) return;
      if (!isDirty) {
        diskContent = d.content;
        baseMtime = d.mtime_ns;
        const keepPos = edTa.selectionStart;
        edTa.value = d.content;
        edTa.setSelectionRange(Math.min(keepPos, d.content.length), Math.min(keepPos, d.content.length));
        recomputeSearchHits();
        renderBackdrop();
        setStatus(`已同步外部修改：${curFile}`);
      } else {
        setStatus(`⚠ 磁盘文件已被外部修改（保存时将提示合并选择）`);
      }
    } catch {}
  }

  /* ---------------- 2. 编辑器 Backdrop 渲染、行号与搜索 ---------------- */
  function getLineCol(pos) {
    const before = edTa.value.slice(0, pos);
    const lines = before.split("\n");
    return { line: lines.length, col: lines[lines.length - 1].length };
  }

  function lineStartOffset(text, line1) {
    const lines = text.split("\n");
    const target = Math.max(1, Math.min(line1, lines.length));
    let off = 0;
    for (let i = 0; i < target - 1; i++) off += lines[i].length + 1;
    return { offset: off, lineText: lines[target - 1] || "", clampedLine: target };
  }

  function recomputeSearchHits() {
    const q = findState.q;
    findState.hits = [];
    if (!q || !edTa) {
      findState.idx = -1;
      updateFindCountUI();
      return;
    }
    let re;
    try {
      re = new RegExp(findState.rx ? q : escRe(q), findState.cs ? "g" : "gi");
    } catch {
      if (findCountEl) findCountEl.textContent = "正则有误";
      return;
    }
    const lines = edTa.value.split("\n");
    let globalOff = 0;
    for (let i = 0; i < lines.length; i++) {
      const lnText = lines[i];
      re.lastIndex = 0;
      let m;
      while ((m = re.exec(lnText)) !== null) {
        if (m[0].length === 0) { re.lastIndex++; continue; }
        findState.hits.push({
          line: i + 1,
          startCol: m.index,
          endCol: m.index + m[0].length,
          absStart: globalOff + m.index,
          absEnd: globalOff + m.index + m[0].length,
        });
      }
      globalOff += lnText.length + 1;
    }
    if (findState.hits.length === 0) findState.idx = -1;
    else if (findState.idx < 0 || findState.idx >= findState.hits.length) findState.idx = 0;
    updateFindCountUI();
  }

  function updateFindCountUI() {
    if (!findCountEl) return;
    if (!findState.q) findCountEl.textContent = "0 / 0";
    else if (!findState.hits.length) findCountEl.textContent = "无匹配";
    else findCountEl.textContent = `${findState.idx + 1} / ${findState.hits.length}`;
  }

  function renderBackdrop() {
    if (!edBackdrop || !edTa) return;
    const lines = edTa.value.split("\n");
    const hitsByLine = new Map();
    findState.hits.forEach((h, idx) => {
      if (!hitsByLine.has(h.line)) hitsByLine.set(h.line, []);
      hitsByLine.get(h.line).push({ ...h, isCur: idx === findState.idx });
    });

    const htmlParts = new Array(lines.length);
    for (let i = 0; i < lines.length; i++) {
      const lnum = i + 1;
      const raw = lines[i];
      let cls = "ed-line";
      if (lnum === curLine) cls += " is-cur";
      if (syncRange && lnum >= syncRange.l1 && lnum <= syncRange.l2) cls += " is-sync";
      if (/^#{1,3}\s/.test(raw)) cls += " syn-head";
      else if (/^(\$\$|:::)/.test(raw)) cls += " syn-fence";

      let inner = "";
      const lineHits = hitsByLine.get(lnum);
      if (!raw) {
        inner = "\u200b";
      } else if (!lineHits) {
        inner = escHtml(raw);
      } else {
        let pos = 0;
        for (const h of lineHits) {
          if (h.startCol > pos) inner += escHtml(raw.slice(pos, h.startCol));
          inner += `<mark class="ed-hit${h.isCur ? " is-current" : ""}">${escHtml(raw.slice(h.startCol, h.endCol))}</mark>`;
          pos = h.endCol;
        }
        if (pos < raw.length) inner += escHtml(raw.slice(pos));
      }
      htmlParts[i] = `<div class="${cls}" data-l="${lnum}">${inner}</div>`;
    }
    edBackdrop.innerHTML = htmlParts.join("");
    syncStageHeight();
  }

  function syncStageHeight() {
    if (!edBackdrop || !edTa || !edScroll) return;
    const h = Math.max(edScroll.clientHeight, edBackdrop.scrollHeight);
    edStage.style.height = `${h}px`;
    edTa.style.height = `${h}px`;
  }

  function scrollEditorToLine(line1, smooth = true) {
    if (!edBackdrop || !edScroll) return;
    const row = edBackdrop.querySelector(`.ed-line[data-l="${line1}"]`);
    if (!row) return;
    const targetTop = Math.max(0, row.offsetTop - edScroll.clientHeight * 0.36);
    edScroll.scrollTo({ top: targetTop, behavior: smooth ? "smooth" : "auto" });
  }

  /* ---------------- 3. 文件加载与保存（含 mtime 乐观锁） ---------------- */
  function markDirty(dirty) {
    isDirty = dirty;
    if (dirtyDot) dirtyDot.classList.toggle("show", dirty);
  }

  function setStatus(msg) {
    if (statusLeft) statusLeft.textContent = msg;
  }

  function updateCursorStatus() {
    if (!edTa || !statusRight) return;
    const { line, col } = getLineCol(edTa.selectionStart);
    curLine = line;
    statusRight.textContent = `${curFile || "-"}  行 ${line}, 列 ${col + 1}`;
  }

  async function refreshFilesList() {
    const r = await fetch("/__api/files", { cache: "no-store" });
    const d = await r.json();
    filesMeta = d.files || [];
    if (!fileSelect) return;
    const prev = curFile || store.get("editor.lastFile") || (filesMeta[0]?.path ?? "");
    fileSelect.replaceChildren();
    for (const f of filesMeta) {
      const opt = document.createElement("option");
      opt.value = f.path;
      opt.textContent = f.path;
      fileSelect.appendChild(opt);
    }
    const chosen = filesMeta.some((f) => f.path === prev) ? prev : (filesMeta[0]?.path ?? "");
    if (chosen && chosen !== curFile) await openFile(chosen);
    else if (chosen) fileSelect.value = chosen;
  }

  async function openFile(relPath, targetLine = null, probeText = "") {
    if (!relPath) return false;
    if (isDirty && curFile && curFile !== relPath) {
      await saveCurrentFile(false);
    }
    if (curFile !== relPath) {
      const r = await fetch(`/__api/file?path=${encodeURIComponent(relPath)}`, { cache: "no-store" });
      if (!r.ok) {
        setStatus(`无法打开文件：${relPath}`);
        return false;
      }
      const d = await r.json();
      curFile = d.path;
      diskContent = d.content;
      baseMtime = d.mtime_ns;
      edTa.value = d.content;
      markDirty(false);
      if (fileSelect) fileSelect.value = curFile;
      store.set("editor.lastFile", curFile);
      syncRange = null;
      recomputeSearchHits();
    }

    if (targetLine != null) {
      const { offset, lineText, clampedLine } = lineStartOffset(edTa.value, targetLine);
      let col = 0;
      let selLen = 0;
      if (probeText) {
        const idx = lineText.indexOf(probeText);
        if (idx >= 0) { col = idx; selLen = probeText.length; }
      }
      curLine = clampedLine;
      renderBackdrop();
      edTa.focus({ preventScroll: true });
      edTa.setSelectionRange(offset + col, offset + col + selLen);
      scrollEditorToLine(clampedLine, true);
    } else {
      curLine = 1;
      renderBackdrop();
      edScroll.scrollTop = 0;
    }
    updateCursorStatus();
    setStatus(`已就绪：${curFile}`);
    return true;
  }

  async function saveCurrentFile(forceOverwrite = false) {
    if (!curFile || !edTa) return;
    clearTimeout(autoSaveTimer);
    const content = edTa.value;
    try {
      const r = await fetch(`/__api/file?path=${encodeURIComponent(curFile)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, base_mtime_ns: baseMtime, force: forceOverwrite }),
      });
      const d = await r.json();
      if (r.status === 409 && d.conflict) {
        const useMine = window.confirm(
          `文件 ${curFile} 在外部（如 VS Code）也发生了修改。\n点击「确定」用当前网页内容覆盖磁盘；点击「取消」加载磁盘最新版本。`
        );
        if (useMine) return saveCurrentFile(true);
        diskContent = d.disk_content;
        baseMtime = d.mtime_ns;
        edTa.value = d.disk_content;
        markDirty(false);
        recomputeSearchHits();
        renderBackdrop();
        setStatus(`已载入外部版本：${curFile}`);
        return;
      }
      if (!r.ok || !d.ok) {
        setStatus(`保存失败：${d.error || r.status}`);
        return;
      }
      diskContent = content;
      baseMtime = d.mtime_ns;
      lastSelfSavedMtime = d.mtime_ns;
      markDirty(false);
      setStatus(`已保存 ${curFile}（右侧实时渲染中…）`);
    } catch (e) {
      setStatus(`保存出错：${e.message || e}`);
    }
  }

  /* ---------------- 4. 类 SyncTeX 正反向精准匹配与配对高亮 ---------------- */
  function extractClickProbe(clientX, clientY) {
    try {
      let node = null, off = 0;
      if (document.caretRangeFromPoint) {
        const rg = document.caretRangeFromPoint(clientX, clientY);
        if (rg) { node = rg.startContainer; off = rg.startOffset; }
      } else if (document.caretPositionFromPoint) {
        const pos = document.caretPositionFromPoint(clientX, clientY);
        if (pos) { node = pos.offsetNode; off = pos.offset; }
      }
      if (node && node.nodeType === Node.TEXT_NODE) {
        const txt = node.nodeValue || "";
        const s = Math.max(0, off - 3);
        const snippet = txt.slice(s, s + 9).trim();
        if (snippet.length >= 2) return snippet;
      }
    } catch {}
    return "";
  }

  function resolveRightTarget(el, preferWrapper = false) {
    if (!el || !docRoot?.contains(el)) return null;
    // 若点击在独立 TeX 图/算法内部，默认跳往对应 .tex 源文件（按住 Shift 则跳往引用它的 .md 行）
    const figTex = el.closest("figure[data-tex]");
    if (figTex && !preferWrapper && !el.closest("figcaption")) {
      return {
        el: figTex,
        file: figTex.dataset.tex,
        line: 1,
        l1: 1,
        l2: 1,
        badge: `${figTex.dataset.tex}（Ctrl+Shift+单击 跳至调用处）`,
      };
    }
    const fine = el.closest("[data-file][data-l]");
    const block = el.closest("[data-file][data-l1]");
    const chosen = fine || block;
    if (!chosen) return null;
    const file = chosen.dataset.file;
    const line = Number(chosen.dataset.l || chosen.dataset.l1 || 1);
    const l1 = Number(chosen.dataset.l1 || line);
    const l2 = Number(chosen.dataset.l2 || line);
    const rangeStr = l1 === l2 ? `${line}` : `${line} (${l1}-${l2})`;
    return { el: chosen, file, line, l1, l2, badge: `${file} : ${rangeStr}` };
  }

  function findRenderedForSource(file, line) {
    if (!docRoot || !file) return null;
    const ef = CSS.escape(file);
    // 1. 若当前编辑的是独立 TeX 算法/图形源码，直接匹配 figure[data-tex]
    const texFig = docRoot.querySelector(`figure[data-tex="${ef}"]`);
    if (texFig) return { el: texFig, l1: 1, l2: Math.max(1, edTa.value.split("\n").length) };

    // 2. 精确行匹配（如段内 <span class="sl" data-l="L">、标题、表格行）
    const exact = docRoot.querySelector(`[data-file="${ef}"][data-l="${line}"]`);
    if (exact) {
      const parentBlock = exact.closest(`[data-file="${ef}"][data-l1]`);
      return {
        el: exact,
        l1: line,
        l2: line,
        parent: parentBlock,
      };
    }

    // 3. 最内层包络区间 l1 <= line <= l2（如多行公式、列表项、定理盒）
    const blocks = Array.from(docRoot.querySelectorAll(`[data-file="${ef}"][data-l1]`));
    let best = null, bestSpan = Infinity;
    for (const b of blocks) {
      const l1 = Number(b.dataset.l1), l2 = Number(b.dataset.l2 || l1);
      if (line >= l1 && line <= l2) {
        const span = l2 - l1;
        if (span <= bestSpan) { best = b; bestSpan = span; }
      }
    }
    if (best) {
      return { el: best, l1: Number(best.dataset.l1), l2: Number(best.dataset.l2 || best.dataset.l1) };
    }

    // 4. 光标位于空行时，吸附同文件距离最近的相邻锚点
    const all = Array.from(docRoot.querySelectorAll(`[data-file="${ef}"][data-l], [data-file="${ef}"][data-l1]`));
    let near = null, nearDist = Infinity;
    for (const node of all) {
      const l1 = Number(node.dataset.l || node.dataset.l1);
      const l2 = Number(node.dataset.l2 || l1);
      const d = line < l1 ? l1 - line : line > l2 ? line - l2 : 0;
      if (d < nearDist) { near = node; nearDist = d; }
    }
    if (near) {
      const l1 = Number(near.dataset.l || near.dataset.l1);
      const l2 = Number(near.dataset.l2 || l1);
      return { el: near, l1, l2 };
    }
    return null;
  }

  function flashPairedHighlight(rightEl, l1, l2, scrollRight = false) {
    clearTimeout(hlClearTimer);
    docRoot?.querySelectorAll(".sync-target-hl").forEach((e) => e.classList.remove("sync-target-hl"));
    if (rightEl) {
      rightEl.classList.add("sync-target-hl");
      if (scrollRight) {
        const paneRect = docRoot.getBoundingClientRect();
        const r = rightEl.getBoundingClientRect();
        if (isSplit) {
          const offsetInPane = r.top - paneRect.top + docRoot.scrollTop;
          docRoot.scrollTo({ top: Math.max(0, offsetInPane - docRoot.clientHeight * 0.32), behavior: "smooth" });
        } else {
          rightEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    }
    syncRange = l1 != null ? { l1, l2: l2 ?? l1 } : null;
    renderBackdrop();
    hlClearTimer = setTimeout(() => {
      docRoot?.querySelectorAll(".sync-target-hl").forEach((e) => e.classList.remove("sync-target-hl"));
      syncRange = null;
      renderBackdrop();
    }, 2400);
  }

  function updatePeerIndicator(scrollIfOut = false) {
    if (!docRoot) return;
    docRoot.querySelectorAll(".sync-peer").forEach((e) => e.classList.remove("sync-peer"));
    if (!isSplit || !linkSync || !curFile) return;
    const hit = findRenderedForSource(curFile, curLine);
    if (!hit?.el) return;
    hit.el.classList.add("sync-peer");
    if (scrollIfOut) {
      const pr = docRoot.getBoundingClientRect();
      const er = hit.el.getBoundingClientRect();
      if (er.top < pr.top + 40 || er.bottom > pr.bottom - 40) {
        const offsetInPane = er.top - pr.top + docRoot.scrollTop;
        docRoot.scrollTo({ top: Math.max(0, offsetInPane - docRoot.clientHeight * 0.35), behavior: "smooth" });
      }
    }
  }

  async function triggerInverseSync(e) {
    const info = resolveRightTarget(e.target, e.shiftKey);
    if (!info) return;
    e.preventDefault();
    e.stopPropagation();
    clearAim();
    const probe = extractClickProbe(e.clientX, e.clientY);
    if (!isSplit) await setSplitMode(true);
    const ok = await openFile(info.file, info.line, probe);
    if (ok) {
      flashPairedHighlight(info.el, info.l1, info.l2, false);
      setStatus(`反向对齐 → ${info.file}:${info.line}`);
    }
  }

  function triggerForwardSync() {
    if (!curFile || !edTa) return;
    const { line } = getLineCol(edTa.selectionStart);
    curLine = line;
    const hit = findRenderedForSource(curFile, line);
    if (!hit) {
      setStatus(`未在渲染页找到 ${curFile}:${line} 对应块`);
      return;
    }
    flashPairedHighlight(hit.el, hit.l1, hit.l2, true);
    setStatus(`正向对齐 → ${curFile}:${line}`);
  }

  /* ---------------- 5. 右侧按住 Ctrl 悬停瞄准镜 ---------------- */
  let aimedEl = null;

  function clearAim() {
    if (aimedEl) { aimedEl.classList.remove("sync-aim"); aimedEl = null; }
    if (aimBadge) aimBadge.classList.remove("show");
  }

  function setupRightPaneSyncEvents() {
    aimBadge = document.createElement("div");
    aimBadge.className = "sync-aim-badge";
    document.body.appendChild(aimBadge);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Control" || e.key === "Meta") root.classList.add("ctrl-aiming");
    });
    document.addEventListener("keyup", (e) => {
      if (e.key === "Control" || e.key === "Meta") {
        root.classList.remove("ctrl-aiming");
        clearAim();
      }
    });
    window.addEventListener("blur", () => {
      root.classList.remove("ctrl-aiming");
      clearAim();
    });

    docRoot.addEventListener("pointermove", (e) => {
      if (!(e.ctrlKey || e.metaKey)) {
        if (aimedEl) clearAim();
        return;
      }
      root.classList.add("ctrl-aiming");
      const info = resolveRightTarget(e.target, e.shiftKey);
      if (!info) { clearAim(); return; }
      if (aimedEl !== info.el) {
        if (aimedEl) aimedEl.classList.remove("sync-aim");
        aimedEl = info.el;
        aimedEl.classList.add("sync-aim");
      }
      aimBadge.textContent = `📍 ${info.badge} · 单击定位`;
      aimBadge.style.left = `${Math.min(window.innerWidth - 240, e.clientX + 14)}px`;
      aimBadge.style.top = `${Math.min(window.innerHeight - 36, e.clientY + 16)}px`;
      aimBadge.classList.add("show");
    });

    docRoot.addEventListener("pointerleave", clearAim);

    // Capture 阶段拦截 Ctrl+Click 或 Alt+Click，确保即使点击在链接或公式上也精准反向跳转
    docRoot.addEventListener("click", (e) => {
      if ((e.ctrlKey || e.metaKey || e.altKey) && e.button === 0) {
        triggerInverseSync(e);
      }
    }, true);

    window.addEventListener("toc:ctrl-jump", async (ev) => {
      const target = ev.detail?.target;
      if (!target) return;
      const info = resolveRightTarget(target, false);
      if (!info) return;
      clearAim();
      if (!isSplit) await setSplitMode(true);
      const ok = await openFile(info.file, info.line);
      if (ok) {
        flashPairedHighlight(info.el, info.l1, info.l2, false);
        setStatus(`目录对齐 → ${info.file}:${info.line}`);
      }
    });
  }

  /* ---------------- 6. 文件内搜索 & 跨章全局搜索 ---------------- */
  function openFindBar(runGlobal = false) {
    if (!isSplit) setSplitMode(true);
    findBar.classList.add("open");
    const sel = edTa.value.slice(edTa.selectionStart, edTa.selectionEnd).trim();
    if (sel && !sel.includes("\n")) findInput.value = sel;
    findInput.focus();
    findInput.select();
    onFindInputChanged();
    if (runGlobal && findInput.value.trim()) runGlobalSearch();
  }

  function closeFindBar() {
    findBar.classList.remove("open");
    globalBox.classList.remove("open");
    findState.q = "";
    findState.hits = [];
    findState.idx = -1;
    renderBackdrop();
    edTa?.focus();
  }

  function onFindInputChanged() {
    findState.q = findInput.value;
    findState.idx = 0;
    recomputeSearchHits();
    renderBackdrop();
    if (findState.hits.length > 0) jumpToHit(0, false);
  }

  function jumpToHit(deltaOrIdx, relative = true) {
    if (!findState.hits.length) return;
    if (relative) {
      findState.idx = (findState.idx + deltaOrIdx + findState.hits.length) % findState.hits.length;
    } else {
      findState.idx = Math.max(0, Math.min(deltaOrIdx, findState.hits.length - 1));
    }
    const h = findState.hits[findState.idx];
    curLine = h.line;
    updateFindCountUI();
    renderBackdrop();
    edTa.setSelectionRange(h.absStart, h.absEnd);
    scrollEditorToLine(h.line, true);
    updateCursorStatus();
    if (linkSync) updatePeerIndicator(true);
  }

  async function runGlobalSearch() {
    const q = findInput.value.trim();
    if (!q) return;
    globalBox.classList.add("open");
    globalBox.innerHTML = `<div class="ed-hit-item"><span class="ed-hit-snip">正在搜索全工程源文件…</span></div>`;
    const url = `/__api/search?q=${encodeURIComponent(q)}&case=${findState.cs ? 1 : 0}&regex=${findState.rx ? 1 : 0}`;
    try {
      const r = await fetch(url, { cache: "no-store" });
      const d = await r.json();
      if (d.error) {
        globalBox.innerHTML = `<div class="ed-hit-item"><span class="ed-hit-snip">${escHtml(d.error)}</span></div>`;
        return;
      }
      const hits = d.hits || [];
      if (!hits.length) {
        globalBox.innerHTML = `<div class="ed-hit-item"><span class="ed-hit-snip">全工程未找到匹配项</span></div>`;
        return;
      }
      globalBox.replaceChildren();
      for (const h of hits) {
        const row = document.createElement("div");
        row.className = "ed-hit-item";
        row.innerHTML = `<span class="ed-hit-loc">${escHtml(h.path)}:${h.line}</span>`
          + `<span class="ed-hit-snip">${escHtml(h.before)}<mark>${escHtml(h.match)}</mark>${escHtml(h.after)}</span>`;
        row.addEventListener("click", async () => {
          await openFile(h.path, h.line);
          const { offset } = lineStartOffset(edTa.value, h.line);
          edTa.setSelectionRange(offset + h.col, offset + h.col + h.len);
          recomputeSearchHits();
          renderBackdrop();
          triggerForwardSync();
        });
        globalBox.appendChild(row);
      }
    } catch (e) {
      globalBox.innerHTML = `<div class="ed-hit-item"><span class="ed-hit-snip">搜索出错：${escHtml(String(e))}</span></div>`;
    }
  }

  /* ---------------- 7. 构建双栏 DOM 与快捷键绑定 ---------------- */
  async function setSplitMode(enable) {
    isSplit = enable;
    store.set("editor.splitOpen", enable ? "1" : "0");
    if (enable) {
      root.setAttribute("data-split", "1");
      splitBtn?.classList.add("is-active");
      if (!filesMeta.length) await refreshFilesList();
      else if (!curFile && filesMeta[0]) await openFile(filesMeta[0].path);
      setTimeout(() => { syncStageHeight(); if (linkSync) updatePeerIndicator(false); }, 30);
    } else {
      root.removeAttribute("data-split");
      splitBtn?.classList.remove("is-active");
      docRoot?.querySelectorAll(".sync-peer").forEach((e) => e.classList.remove("sync-peer"));
    }
  }

  function buildWorkbenchDOM() {
    const savedW = store.get("editor.splitWidth");
    if (savedW) root.style.setProperty("--split-left", savedW);

    edPane = document.createElement("section");
    edPane.id = "ed-pane";
    edPane.setAttribute("aria-label", "Markdown 与 TeX 源码编辑面板");
    edPane.innerHTML = `
      <div class="ed-topbar">
        <select class="ed-file-select" title="切换源文件"></select>
        <span class="ed-dirty-dot" title="有未保存更改">●</span>
        <button type="button" class="ed-btn" data-ed="find" title="当前文件搜索 (Ctrl+F)">🔍 搜索</button>
        <button type="button" class="ed-btn" data-ed="global-find" title="跨章节全文搜索 (Ctrl+Shift+F)">🌐 全局</button>
        <button type="button" class="ed-btn" data-ed="sync-fwd" title="正向对齐到右侧渲染位置 (Ctrl+Alt+J / Ctrl+单击)">⇥ 对齐</button>
        <button type="button" class="ed-btn" data-ed="link-sync" title="光标移动时实时联动高亮右侧对应句">🔗 联动</button>
        <button type="button" class="ed-btn" data-ed="auto-save" title="停笔 350ms 自动写回磁盘并实时局部渲染">⚡ 自动存</button>
        <button type="button" class="ed-btn" data-ed="save" title="立即保存 (Ctrl+S)">保存</button>
      </div>
      <div class="ed-findbar">
        <input type="text" class="ed-find-input" placeholder="查找源码（Enter 下一个，Shift+Enter 上一个）…">
        <span class="ed-find-count">0 / 0</span>
        <button type="button" class="ed-btn" data-find="prev" title="上一个 (Shift+Enter)">▲</button>
        <button type="button" class="ed-btn" data-find="next" title="下一个 (Enter)">▼</button>
        <button type="button" class="ed-btn" data-find="case" title="区分大小写">Aa</button>
        <button type="button" class="ed-btn" data-find="regex" title="正则表达式">.*</button>
        <button type="button" class="ed-btn" data-find="all" title="跨全部文件搜索 (Ctrl+Shift+F)">搜全篇</button>
        <button type="button" class="ed-btn" data-find="close" title="关闭搜索 (Esc)">✕</button>
      </div>
      <div class="ed-global-results"></div>
      <div class="ed-scroll">
        <div class="ed-stage">
          <div class="ed-backdrop" aria-hidden="true"></div>
          <textarea class="ed-ta" spellcheck="false" autocomplete="off" autocapitalize="off"></textarea>
        </div>
      </div>
      <div class="ed-statusbar">
        <span class="ed-st-left">Ctrl+单击 正反向对齐 · Ctrl+\\ 收起双栏</span>
        <span class="ed-st-right">-</span>
      </div>
    `;

    resizer = document.createElement("div");
    resizer.id = "split-resizer";
    resizer.title = "拖拽调整左右分栏宽度；双击恢复默认比例";

    document.body.insertBefore(edPane, docRoot);
    document.body.insertBefore(resizer, docRoot);

    fileSelect = edPane.querySelector(".ed-file-select");
    dirtyDot = edPane.querySelector(".ed-dirty-dot");
    findBar = edPane.querySelector(".ed-findbar");
    findInput = edPane.querySelector(".ed-find-input");
    findCountEl = edPane.querySelector(".ed-find-count");
    caseBtn = edPane.querySelector('[data-find="case"]');
    regexBtn = edPane.querySelector('[data-find="regex"]');
    globalBox = edPane.querySelector(".ed-global-results");
    autoSaveBtn = edPane.querySelector('[data-ed="auto-save"]');
    linkSyncBtn = edPane.querySelector('[data-ed="link-sync"]');
    statusLeft = edPane.querySelector(".ed-st-left");
    statusRight = edPane.querySelector(".ed-st-right");
    edScroll = edPane.querySelector(".ed-scroll");
    edStage = edPane.querySelector(".ed-stage");
    edBackdrop = edPane.querySelector(".ed-backdrop");
    edTa = edPane.querySelector(".ed-ta");

    autoSaveBtn.classList.toggle("is-on", autoSave);
    linkSyncBtn.classList.toggle("is-on", linkSync);

    fileSelect.addEventListener("change", () => openFile(fileSelect.value));

    edPane.querySelector('[data-ed="find"]').onclick = () => openFindBar(false);
    edPane.querySelector('[data-ed="global-find"]').onclick = () => openFindBar(true);
    edPane.querySelector('[data-ed="sync-fwd"]').onclick = () => triggerForwardSync();
    edPane.querySelector('[data-ed="save"]').onclick = () => saveCurrentFile(false);
    autoSaveBtn.onclick = () => {
      autoSave = !autoSave;
      store.set("editor.autoSave", autoSave ? "1" : "0");
      autoSaveBtn.classList.toggle("is-on", autoSave);
      setStatus(autoSave ? "已开启停笔自动保存" : "已切换为 Ctrl+S 手动保存");
    };
    linkSyncBtn.onclick = () => {
      linkSync = !linkSync;
      store.set("editor.linkSync", linkSync ? "1" : "0");
      linkSyncBtn.classList.toggle("is-on", linkSync);
      updatePeerIndicator(linkSync);
    };

    findInput.addEventListener("input", onFindInputChanged);
    findInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (e.ctrlKey || e.metaKey) runGlobalSearch();
        else jumpToHit(e.shiftKey ? -1 : 1, true);
      } else if (e.key === "Escape") {
        e.preventDefault();
        closeFindBar();
      }
    });
    edPane.querySelector('[data-find="prev"]').onclick = () => jumpToHit(-1, true);
    edPane.querySelector('[data-find="next"]').onclick = () => jumpToHit(1, true);
    caseBtn.onclick = () => {
      findState.cs = !findState.cs;
      caseBtn.classList.toggle("is-on", findState.cs);
      onFindInputChanged();
    };
    regexBtn.onclick = () => {
      findState.rx = !findState.rx;
      regexBtn.classList.toggle("is-on", findState.rx);
      onFindInputChanged();
    };
    edPane.querySelector('[data-find="all"]').onclick = () => runGlobalSearch();
    edPane.querySelector('[data-find="close"]').onclick = () => closeFindBar();

    // 文本输入与快捷键
    edTa.addEventListener("input", () => {
      markDirty(edTa.value !== diskContent);
      updateCursorStatus();
      recomputeSearchHits();
      renderBackdrop();
      if (autoSave && isDirty) {
        clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(() => saveCurrentFile(false), 360);
      }
    });

    const onCaretMove = () => {
      const prevLine = curLine;
      updateCursorStatus();
      if (curLine !== prevLine) {
        edBackdrop.querySelector(".ed-line.is-cur")?.classList.remove("is-cur");
        edBackdrop.querySelector(`.ed-line[data-l="${curLine}"]`)?.classList.add("is-cur");
        if (linkSync) {
          clearTimeout(peerTimer);
          peerTimer = setTimeout(() => updatePeerIndicator(false), 75);
        }
      }
    };
    edTa.addEventListener("keyup", onCaretMove);
    edTa.addEventListener("select", onCaretMove);

    // 左侧 Ctrl+单击 / Alt+单击 / 单击左侧行号槽 -> 正向对齐右侧渲染行
    edTa.addEventListener("mousedown", (e) => {
      if (e.button !== 0) return;
      const clickedGutter = e.offsetX < 52;
      if (e.ctrlKey || e.metaKey || e.altKey || clickedGutter) {
        setTimeout(() => {
          onCaretMove();
          triggerForwardSync();
        }, 0);
      } else {
        setTimeout(onCaretMove, 0);
      }
    });

    edTa.addEventListener("keydown", (e) => {
      if (e.key === "Tab" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        const s = edTa.selectionStart, end = edTa.selectionEnd;
        edTa.setRangeText("  ", s, end, "end");
        edTa.dispatchEvent(new Event("input"));
      }
    });

    // 中缝分割条拖拽
    resizer.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      resizer.setPointerCapture(e.pointerId);
      document.body.classList.add("split-dragging");
      const move = (ev) => {
        const px = Math.max(280, Math.min(window.innerWidth - 340, ev.clientX));
        const pct = `${((px / window.innerWidth) * 100).toFixed(2)}vw`;
        root.style.setProperty("--split-left", pct);
        syncStageHeight();
      };
      const up = () => {
        document.body.classList.remove("split-dragging");
        resizer.removeEventListener("pointermove", move);
        store.set("editor.splitWidth", root.style.getPropertyValue("--split-left"));
      };
      resizer.addEventListener("pointermove", move);
      resizer.addEventListener("pointerup", up, { once: true });
      resizer.addEventListener("pointercancel", up, { once: true });
    });
    resizer.addEventListener("dblclick", () => {
      root.style.removeProperty("--split-left");
      store.set("editor.splitWidth", null);
      syncStageHeight();
    });
    window.addEventListener("resize", () => { if (isSplit) syncStageHeight(); });

    // 全局键盘快捷键
    document.addEventListener("keydown", (e) => {
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key === "\\") {
        e.preventDefault();
        setSplitMode(!isSplit);
      } else if (mod && (e.key === "s" || e.key === "S") && isSplit) {
        e.preventDefault();
        saveCurrentFile(false);
      } else if (mod && e.shiftKey && (e.key === "f" || e.key === "F")) {
        e.preventDefault();
        openFindBar(true);
      } else if (mod && !e.shiftKey && (e.key === "f" || e.key === "F") && isSplit) {
        e.preventDefault();
        openFindBar(false);
      } else if (
        isSplit &&
        ((mod && e.altKey && (e.key === "j" || e.key === "J")) || (e.altKey && !mod && e.key === "Enter"))
      ) {
        e.preventDefault();
        triggerForwardSync();
      }
    });
  }

  function attachSplitToolbarButton() {
    const attach = () => {
      const bar = document.getElementById("reader-bar") || document.querySelector(".reader-bar");
      if (!bar || bar.querySelector('[data-role="split"]')) return;
      splitBtn = document.createElement("button");
      splitBtn.type = "button";
      splitBtn.dataset.role = "split";
      splitBtn.textContent = "◫ 双栏";
      splitBtn.title = "开启或关闭源码双栏编辑与对照模式（快捷键 Ctrl+\\）";
      splitBtn.classList.toggle("is-active", isSplit);
      splitBtn.onclick = () => setSplitMode(!isSplit);
      const toc = bar.querySelector('[data-role="toc"]');
      if (toc && toc.nextSibling) bar.insertBefore(splitBtn, toc.nextSibling);
      else bar.prepend(splitBtn);
    };
    attach();
    setTimeout(attach, 30);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    docRoot = document.getElementById("doc-root");
    if (!docRoot) return;
    buildWorkbenchDOM();
    attachSplitToolbarButton();
    setupRightPaneSyncEvents();

    try {
      rawChildren = await fetchRawChildren();
      liveReady = rawChildren.length === docRoot.children.length;
    } catch {}

    if (isSplit) await setSplitMode(true);
    liveLoop();
  });
})();
