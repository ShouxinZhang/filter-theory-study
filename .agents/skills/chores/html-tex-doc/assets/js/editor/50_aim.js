  /* ---------------- 5. 右侧按住 Ctrl 悬停瞄准镜 ---------------- */
  let aimedEl = null;

  function clearAim() {
    if (aimedEl) { aimedEl.classList.remove("sync-aim"); aimedEl = null; }
    if (aimBadge) aimBadge.classList.remove("show");
  }

  function setupRightPaneSyncEvents() {
    aimBadge = document.createElement("div");
    aimBadge.className = "sync-aim-badge ui-badge";
    document.body.appendChild(aimBadge);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Control" || e.key === "Meta") docRoot?.classList.add("ctrl-aiming");
    });
    document.addEventListener("keyup", (e) => {
      if (e.key === "Control" || e.key === "Meta") {
        docRoot?.classList.remove("ctrl-aiming");
        clearAim();
      }
    });
    window.addEventListener("blur", () => {
      docRoot?.classList.remove("ctrl-aiming");
      clearAim();
    });

    docRoot.addEventListener("pointermove", (e) => {
      if (!(e.ctrlKey || e.metaKey)) {
        if (aimedEl) clearAim();
        return;
      }
      docRoot?.classList.add("ctrl-aiming");
      const info = resolveRightTarget(e.target, e.shiftKey);
      if (!info) { clearAim(); return; }
      if (aimedEl !== info.el) {
        if (aimedEl) aimedEl.classList.remove("sync-aim");
        aimedEl = info.el;
        aimedEl.classList.add("sync-aim");
      }
      aimBadge.textContent = `${info.badge} · 单击定位`;
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

