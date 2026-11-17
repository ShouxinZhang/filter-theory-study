  // 延后开启"跳过屏幕外的块"（原因见 05_page.css）；双栏开合前由 editor 调用 window.HTD.skipOffscreen() 提前开启
  const enableSkipOffscreen = () => getDocPane().classList.add("skip-offscreen");
  window.HTD.skipOffscreen = enableSkipOffscreen;
  function scheduleSkipOffscreen() {
    const later = () => setTimeout(() => (window.requestIdleCallback || setTimeout)(enableSkipOffscreen), 2500);
    if (document.readyState === "complete") later();
    else window.addEventListener("load", later, { once: true });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupResize();
    setupBar();
    setupTocDrawer();
    bindInlineToc();
    const { total } = collectHeadingsTree();
    if (tocBtn) tocBtn.style.display = total ? "" : "none";
    setupPreview();
    setupZoom();
    scheduleSkipOffscreen();
  });

  window.addEventListener("doc:patched", () => {
    bindInlineToc();
    if (drawer?.classList.contains("open")) renderDrawerTree();
    else {
      const { total } = collectHeadingsTree();
      if (tocBtn) tocBtn.style.display = total ? "" : "none";
    }
  });
})();
