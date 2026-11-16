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

  function scrollEditorToLine(line1, smooth = false) {
    if (!edBackdrop || !edScroll) return;
    const row = edBackdrop.querySelector(`.ed-line[data-l="${line1}"]`);
    if (!row) return;
    const targetTop = Math.max(0, row.offsetTop - edScroll.clientHeight * 0.36);
    edScroll.scrollTo({ top: targetTop, behavior: smooth ? "smooth" : "auto" });
  }

