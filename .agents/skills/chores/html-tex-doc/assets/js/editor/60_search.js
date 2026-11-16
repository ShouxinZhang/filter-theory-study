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
    globalBox.innerHTML = `<div class="ed-hit-item ui-row"><span class="ed-hit-snip">正在搜索全工程源文件…</span></div>`;
    const url = `/__api/search?q=${encodeURIComponent(q)}&case=${findState.cs ? 1 : 0}&regex=${findState.rx ? 1 : 0}`;
    try {
      const r = await fetch(url, { cache: "no-store" });
      const d = await r.json();
      if (d.error) {
        globalBox.innerHTML = `<div class="ed-hit-item ui-row"><span class="ed-hit-snip">${escHtml(d.error)}</span></div>`;
        return;
      }
      const hits = d.hits || [];
      if (!hits.length) {
        globalBox.innerHTML = `<div class="ed-hit-item ui-row"><span class="ed-hit-snip">全工程未找到匹配项</span></div>`;
        return;
      }
      globalBox.replaceChildren();
      for (const h of hits) {
        const row = document.createElement("div");
        row.className = "ed-hit-item ui-row";
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
      globalBox.innerHTML = `<div class="ed-hit-item ui-row"><span class="ed-hit-snip">搜索出错：${escHtml(String(e))}</span></div>`;
    }
  }

