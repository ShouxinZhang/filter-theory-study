  /* ---------------- 3. 文件加载与保存（含 mtime 乐观锁） ---------------- */
  function markDirty(dirty) {
    isDirty = dirty;
    if (dirtyDot) dirtyDot.classList.toggle("show", dirty);
    if (saveBtn) saveBtn.classList.toggle("is-dirty", dirty);
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
      scrollEditorToLine(clampedLine, false);
    } else {
      curLine = 1;
      renderBackdrop();
      edScroll.scrollTop = 0;
    }
    updateCursorStatus();
    setStatus(`已就绪：${curFile}`);
    return true;
  }

  async function saveCurrentFile(forceOverwrite = true) {
    if (!curFile || !edTa) return;
    clearTimeout(autoSaveTimer);
    if (saveInFlight) {
      saveQueued = true;
      return;
    }
    saveInFlight = true;
    const targetFile = curFile;
    const content = edTa.value;
    try {
      const r = await fetch(`/__api/file?path=${encodeURIComponent(targetFile)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, base_mtime_ns: baseMtime, force: forceOverwrite }),
      });
      const d = await r.json();
      if (!r.ok || !d.ok) {
        setStatus(`保存失败：${d.error || r.status}`);
        return;
      }
      if (curFile === targetFile) {
        diskContent = content;
        baseMtime = d.mtime_ns;
        lastSelfSavedMtime = d.mtime_ns;
        if (edTa.value === content) markDirty(false);
      }
      setStatus(`已保存 ${targetFile}（右侧实时渲染中…）`);
    } catch (e) {
      setStatus(`保存出错：${e.message || e}`);
    } finally {
      saveInFlight = false;
      if (saveQueued) {
        saveQueued = false;
        saveCurrentFile(true);
      }
    }
  }

  function flushDirtyOnLeave() {
    if (!isDirty || !curFile || !edTa || !autoSave) return;
    clearTimeout(autoSaveTimer);
    const content = edTa.value;
    try {
      fetch(`/__api/file?path=${encodeURIComponent(curFile)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, force: true }),
        keepalive: true,
      });
    } catch {}
  }

