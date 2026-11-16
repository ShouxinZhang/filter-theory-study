  document.addEventListener("DOMContentLoaded", async () => {
    docRoot = document.getElementById("doc-root");
    if (!docRoot) return;
    buildWorkbenchDOM();
    attachSplitToolbarButton();
    setupRightPaneSyncEvents();

    try {
      rawChildren = await fetchRawChildren();
      liveReady = rawChildren.length === docRoot.children.length;
    } catch {}

    if (isSplit) await setSplitMode(true);
    liveLoop();
  });
})();
