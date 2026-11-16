  /* ---------------- 1. 单栏栏宽 ---------------- */
  const MIN_PX = 420;
  const applyMeasure = (px) => {
    if (px == null) root.style.removeProperty("--measure");
    else root.style.setProperty("--measure", `${Math.round(px)}px`);
  };
  applyMeasure(store.get("reader.measure") && Number(store.get("reader.measure")));

  function setupResize() {
    const badge = document.createElement("div");
    badge.className = "measure-badge ui-badge";
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
        // 栏宽变化会触发全文重排：把同一帧内的多次 pointermove 合并为一次
        let pendingW = null, frame = 0;
        const flush = () => {
          frame = 0;
          if (pendingW == null) return;
          applyMeasure(pendingW);
          badge.textContent = `${Math.round(pendingW)} px · 约 ${Math.round((pendingW - 64) / fontPx)} 字/行`;
          pendingW = null;
        };
        const move = (ev) => {
          pendingW = Math.max(MIN_PX, Math.min(window.innerWidth, startW + 2 * sign * (ev.clientX - startX)));
          if (!frame) frame = requestAnimationFrame(flush);
        };
        const up = () => {
          if (frame) cancelAnimationFrame(frame);
          flush();
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

