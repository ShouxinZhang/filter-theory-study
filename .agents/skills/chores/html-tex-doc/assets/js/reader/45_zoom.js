  /* ---------------- 5. 插图点击放大 ---------------- */
  function setupZoom() {
    const box = document.createElement("div");
    box.className = "fig-zoom";
    const big = document.createElement("img");
    big.alt = "";
    box.appendChild(big);
    document.body.appendChild(box);
    const close = () => box.classList.remove("open");
    document.addEventListener("click", (e) => {
      if (box.contains(e.target)) { close(); return; }
      const img = e.target.closest?.("figure.fig img");
      if (!img || e.ctrlKey || e.metaKey || e.altKey) return;   // 带修饰键的点击留给源码定位
      big.src = img.currentSrc || img.src;
      if (img.naturalWidth && img.naturalHeight) box.style.setProperty("--ar", String(img.naturalWidth / img.naturalHeight));
      box.classList.add("open");
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  }

