  document.addEventListener("DOMContentLoaded", () => {
    setupResize();
    setupBar();
    setupTocDrawer();
    bindInlineToc();
    const { total } = collectHeadingsTree();
    if (tocBtn) tocBtn.style.display = total ? "" : "none";
    setupPreview();
    setupZoom();
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
