  /* ---------------- 7. 构建双栏 DOM 与快捷键绑定 ---------------- */
  async function setSplitMode(enable) {
    window.HTD.skipOffscreen?.();   // 开合双栏会改变正文栏宽：先让屏幕外的块跳过重排
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
    const ICO = {
      search: ccIco('<circle cx="7" cy="7" r="4.5"/><path d="m10.5 10.5 3 3"/>'),
      globe: ccIco('<circle cx="8" cy="8" r="5.8"/><path d="M2.5 8h11M8 2.2c1.8 1.8 1.8 9.8 0 11.6M8 2.2c-1.8 1.8-1.8 9.8 0 11.6"/>'),
      sync: ccIco('<path d="M2.5 8h8M7.5 5l3 3-3 3M13.5 3.5v9"/>'),
      link: ccIco('<path d="M6.5 9.5 9.5 6.5M5.2 6.8l-1.4 1.4a2.4 2.4 0 0 0 3.4 3.4l1.4-1.4M10.8 9.2l1.4-1.4a2.4 2.4 0 0 0-3.4-3.4L7.4 5.8"/>'),
      bolt: ccIco('<path d="M9 1.8 4.2 8.8H8L7 14.2l4.8-7H8L9 1.8Z"/>'),
      history: ccIco('<path d="M3 8a5 5 0 1 0 1.4-3.5L3 6M3 2.8V6h3.2M8 5.2V8l2 1.2"/>'),
      more: ccIco('<circle cx="3.5" cy="8" r="1" fill="currentColor" stroke="none"/><circle cx="8" cy="8" r="1" fill="currentColor" stroke="none"/><circle cx="12.5" cy="8" r="1" fill="currentColor" stroke="none"/>'),
      save: ccIco('<path d="M3 8.5 6.2 11.5 13 4.5"/>'),
    };
    edPane.innerHTML = `
      <div class="ed-topbar ui-bar">
        <select class="ed-file-select ui-input" title="切换源文件"></select>
        <span class="ed-dirty-dot" title="有未保存更改">●</span>
        <button type="button" class="ed-btn ui-btn" data-ed="find" title="当前文件搜索 (Ctrl+F)">${ICO.search}<span>搜索</span></button>
        <button type="button" class="ed-btn ui-btn" data-ed="more" title="更多操作与增量历史">${ICO.more}</button>
        <button type="button" class="ed-btn ui-btn" data-ed="save" title="立即保存 (Ctrl+S)">${ICO.save}<span>保存</span></button>
        <div class="ed-menu ui-popover" role="menu">
          <button type="button" class="ed-menu-item ui-row" data-ed="global-find">${ICO.globe}<span>跨文件全文搜索</span><span class="ed-k ui-kbd">Ctrl+Shift+F</span></button>
          <button type="button" class="ed-menu-item ui-row" data-ed="sync-fwd">${ICO.sync}<span>正向对齐到右侧</span><span class="ed-k ui-kbd">Ctrl+Alt+J</span></button>
          <div class="ed-menu-sep ui-sep"></div>
          <button type="button" class="ed-menu-item ui-row" data-ed="link-sync">${ICO.link}<span>光标联动右侧指示</span><span class="ed-chk"></span></button>
          <button type="button" class="ed-menu-item ui-row" data-ed="auto-save">${ICO.bolt}<span>实时同步到右侧</span><span class="ed-chk"></span></button>
          <div class="ed-menu-sep ui-sep"></div>
          <button type="button" class="ed-menu-item ui-row" data-ed="history">${ICO.history}<span>增量变更历史 / 撤回</span></button>
        </div>
      </div>
      <div class="ed-findbar ui-bar">
        <input type="text" class="ed-find-input ui-input" placeholder="查找源码（Enter 下一个，Shift+Enter 上一个）…">
        <span class="ed-find-count">0 / 0</span>
        <button type="button" class="ed-btn ui-btn" data-find="prev" title="上一个 (Shift+Enter)">▲</button>
        <button type="button" class="ed-btn ui-btn" data-find="next" title="下一个 (Enter)">▼</button>
        <button type="button" class="ed-btn ui-btn" data-find="case" title="区分大小写">Aa</button>
        <button type="button" class="ed-btn ui-btn" data-find="regex" title="正则表达式">.*</button>
        <button type="button" class="ed-btn ui-btn" data-find="all" title="跨全部文件搜索 (Ctrl+Shift+F)">全篇</button>
        <button type="button" class="ed-btn ui-btn" data-find="close" title="关闭搜索 (Esc)">✕</button>
      </div>
      <div class="ed-global-results"></div>
      <div class="ed-history-panel"></div>
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
    saveBtn = edPane.querySelector('[data-ed="save"]');
    edMenu = edPane.querySelector(".ed-menu");
    const moreBtn = edPane.querySelector('[data-ed="more"]');
    findBar = edPane.querySelector(".ed-findbar");
    findInput = edPane.querySelector(".ed-find-input");
    findCountEl = edPane.querySelector(".ed-find-count");
    caseBtn = edPane.querySelector('[data-find="case"]');
    regexBtn = edPane.querySelector('[data-find="regex"]');
    globalBox = edPane.querySelector(".ed-global-results");
    histPanel = edPane.querySelector(".ed-history-panel");
    autoSaveChk = edMenu.querySelector('[data-ed="auto-save"] .ed-chk');
    linkSyncChk = edMenu.querySelector('[data-ed="link-sync"] .ed-chk');
    statusLeft = edPane.querySelector(".ed-st-left");
    statusRight = edPane.querySelector(".ed-st-right");
    edScroll = edPane.querySelector(".ed-scroll");
    edStage = edPane.querySelector(".ed-stage");
    edBackdrop = edPane.querySelector(".ed-backdrop");
    edTa = edPane.querySelector(".ed-ta");

    const syncMenuChecks = () => {
      if (autoSaveChk) autoSaveChk.textContent = autoSave ? "✓" : "";
      if (linkSyncChk) linkSyncChk.textContent = linkSync ? "✓" : "";
    };
    syncMenuChecks();

    const closeMenu = () => edMenu?.classList.remove("open");
    moreBtn.onclick = (e) => {
      e.stopPropagation();
      edMenu.classList.toggle("open");
    };
    document.addEventListener("mousedown", (e) => {
      if (edMenu?.classList.contains("open") && !edMenu.contains(e.target) && !moreBtn.contains(e.target)) {
        closeMenu();
      }
    });

    async function openHistoryPanel() {
      if (!curFile || !histPanel) return;
      if (histPanel.classList.contains("open")) {
        histPanel.classList.remove("open");
        return;
      }
      histPanel.innerHTML = `<div class="ed-hist-head"><span>加载增量记录中…</span></div>`;
      histPanel.classList.add("open");
      try {
        const r = await fetch(`/__api/history?path=${encodeURIComponent(curFile)}`, { cache: "no-store" });
        const d = await r.json();
        const ops = d.ops || [];
        const closeBtnHtml = `<button type="button" class="ed-btn ui-btn" data-hist-close>✕</button>`;
        if (!ops.length) {
          histPanel.innerHTML = `<div class="ed-hist-head"><span>${escHtml(curFile)} 暂无增量修改记录</span>${closeBtnHtml}</div>`;
        } else {
          histPanel.innerHTML =
            `<div class="ed-hist-head"><span>${escHtml(curFile)} 增量记录（SQLite WAL 仅存变更行）</span>${closeBtnHtml}</div>` +
            ops
              .map((op) => {
                const t = new Date(op.ts * 1000).toLocaleTimeString([], { hour12: false });
                const tag = op.source === "rollback" ? "回滚" : "保存";
                return `<div class="ed-hit-item ui-row" data-op-id="${op.id}">`
                  + `<span class="ed-hit-loc">${t} · ${tag}</span>`
                  + `<span class="ed-hit-snip">${escHtml(op.summary)}</span>`
                  + `<span class="ed-k ui-kbd">撤回至此步</span></div>`;
              })
              .join("");
        }
        histPanel.querySelector("[data-hist-close]")?.addEventListener("click", () => histPanel.classList.remove("open"));
        histPanel.querySelectorAll("[data-op-id]").forEach((row) => {
          row.addEventListener("click", async () => {
            const opId = Number(row.dataset.opId);
            const rr = await fetch("/__api/rollback", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ path: curFile, id: opId }),
            });
            const rd = await rr.json();
            if (rr.ok && rd.ok) {
              diskContent = rd.content;
              baseMtime = rd.mtime_ns;
              lastSelfSavedMtime = rd.mtime_ns;
              edTa.value = rd.content;
              markDirty(false);
              recomputeSearchHits();
              renderBackdrop();
              histPanel.classList.remove("open");
              setStatus(`已增量回滚 ${curFile}（可通过最新记录再次撤回）`);
            }
          });
        });
      } catch (e) {
        histPanel.innerHTML = `<div class="ed-hist-head"><span>读取失败：${escHtml(String(e))}</span></div>`;
      }
    }

    fileSelect.addEventListener("change", () => {
      histPanel?.classList.remove("open");
      openFile(fileSelect.value);
    });

    edPane.querySelector('[data-ed="find"]').onclick = () => openFindBar(false);
    edMenu.querySelector('[data-ed="global-find"]').onclick = () => { closeMenu(); openFindBar(true); };
    edMenu.querySelector('[data-ed="sync-fwd"]').onclick = () => { closeMenu(); triggerForwardSync(); };
    edPane.querySelector('[data-ed="save"]').onclick = () => saveCurrentFile(true);
    edMenu.querySelector('[data-ed="history"]').onclick = () => { closeMenu(); openHistoryPanel(); };
    edMenu.querySelector('[data-ed="auto-save"]').onclick = () => {
      autoSave = !autoSave;
      store.set("editor.autoSave", autoSave ? "1" : "0");
      syncMenuChecks();
      setStatus(autoSave ? "实时同步已开启：停笔即保存并刷新右侧" : "实时同步已关闭：按 Ctrl+S 保存后才刷新右侧");
    };
    edMenu.querySelector('[data-ed="link-sync"]').onclick = () => {
      linkSync = !linkSync;
      store.set("editor.linkSync", linkSync ? "1" : "0");
      syncMenuChecks();
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
        autoSaveTimer = setTimeout(() => saveCurrentFile(false), REALTIME_DELAY);
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
    window.addEventListener("pagehide", flushDirtyOnLeave);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") flushDirtyOnLeave();
    });
    window.addEventListener("beforeunload", (e) => {
      if (isDirty && !autoSave) {
        e.preventDefault();
        e.returnValue = "";
      } else {
        flushDirtyOnLeave();
      }
    });

    // 全局键盘快捷键
    document.addEventListener("keydown", (e) => {
      const mod = e.ctrlKey || e.metaKey;
      if ((mod && !e.altKey && !e.shiftKey && (e.code === "Backslash" || e.key === "\\")) || (e.altKey && !mod && !e.shiftKey && e.code === "Backslash")) {
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
      splitBtn.className = "ui-btn";
      splitBtn.dataset.role = "split";
      splitBtn.innerHTML = `${ccIco('<rect x="2" y="2.5" width="12" height="11" rx="1.8"/><path d="M8 2.5v11"/>')}<span>双栏</span>`;
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

