  /* ---------------- 1. 右侧 #doc-root 块级无闪烁热刷新 ---------------- */
  let liveVer = -1, rawChildren = [], liveReady = false;

  const parseHtmlChildren = (htmlText) =>
    Array.from(new DOMParser().parseFromString(htmlText, "text/html").body.children).map((e) => e.outerHTML);

  async function fetchRawChildren() {
    const res = await fetch(api("__raw"), { cache: "no-store" });
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
        const res = await fetch(api(`__live?v=${liveVer}`), { cache: "no-store" });
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
      const r = await fetch(api(`__api/file?path=${encodeURIComponent(curFile)}`), { cache: "no-store" });
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
