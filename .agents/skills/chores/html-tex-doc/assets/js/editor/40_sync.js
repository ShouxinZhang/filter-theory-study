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
          docRoot.scrollTo({ top: Math.max(0, offsetInPane - docRoot.clientHeight * 0.32), behavior: "auto" });
        } else {
          rightEl.scrollIntoView({ behavior: "auto", block: "center" });
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
        docRoot.scrollTo({ top: Math.max(0, offsetInPane - docRoot.clientHeight * 0.35), behavior: "auto" });
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

