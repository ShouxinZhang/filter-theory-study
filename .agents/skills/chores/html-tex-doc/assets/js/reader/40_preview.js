  /* ---------------- 4. 链接悬停预览 ---------------- */
  // HIDE_DELAY 只留 50ms：够鼠标越过链接与卡片之间的 8px 缝隙移进卡片，又近乎即时消失
  const SHOW_DELAY = 60, HIDE_DELAY = 50;
  let pop, showTimer, hideTimer, current;

  const hrefOf = (a) => a.getAttribute("href") || a.getAttributeNS(XLINK, "href") || "";
  const isHeading = (el) => /^H[1-6]$/.test(el.tagName);

  function buildPreview(id) {
    const target = document.getElementById(id);
    if (!target) return null;
    const nodes = [target];
    if (isHeading(target)) {
      let n = target.nextElementSibling;
      while (n && nodes.length < 3 && !isHeading(n)) { nodes.push(n); n = n.nextElementSibling; }
    } else if (target.matches("div.thm") && target.nextElementSibling?.matches("div.proof")) {
      nodes.push(target.nextElementSibling);
    }
    const box = document.createElement("div");
    for (const n of nodes) {
      const c = n.cloneNode(true);
      c.removeAttribute("id");
      c.querySelectorAll("[id]").forEach((e) => e.removeAttribute("id"));
      box.appendChild(c);
    }
    return box;
  }

  function place(anchorEl) {
    const r = anchorEl.getBoundingClientRect(), gap = 8, vw = window.innerWidth, vh = window.innerHeight;
    pop.style.left = "0px"; pop.style.top = "0px";
    const pr = pop.getBoundingClientRect();
    const left = Math.min(Math.max(8, r.left + r.width / 2 - pr.width / 2), vw - pr.width - 8);
    let top = r.bottom + gap;
    if (top + pr.height > vh - 8 && r.top - gap - pr.height > 8) top = r.top - gap - pr.height;
    top = Math.max(8, Math.min(top, vh - pr.height - 8));
    pop.style.left = `${left}px`; pop.style.top = `${top}px`;
  }

  function show(a) {
    if (getDocPane().classList.contains("ctrl-aiming")) return;
    const id = decodeURIComponent(hrefOf(a).slice(1));
    const content = buildPreview(id);
    if (!content) return;
    const label = a.textContent.trim() || a.getAttributeNS(XLINK, "title") || id;
    pop.replaceChildren();
    const head = document.createElement("div");
    head.className = "pv-head";
    head.textContent = `预览 · ${label}（单击链接跳转）`;
    pop.append(head, content);
    current = a;
    place(a);
    pop.classList.add("show");
  }
  function hide() { if (pop) pop.classList.remove("show"); current = null; }

  function setupPreview() {
    pop = document.createElement("div");
    pop.className = "xref-preview ui-popover";
    pop.setAttribute("role", "tooltip");
    document.body.appendChild(pop);

    document.addEventListener("pointerover", (e) => {
      if (e.pointerType === "touch" || e.ctrlKey || e.metaKey) return;
      const a = e.target.closest?.("a");
      if (!a || pop.contains(a) || a.closest("nav.toc, .toc-drawer")) return;
      if (!hrefOf(a).startsWith("#") || hrefOf(a).length < 2) return;
      clearTimeout(hideTimer);
      if (a === current) return;
      clearTimeout(showTimer);
      showTimer = setTimeout(() => show(a), SHOW_DELAY);
    });
    document.addEventListener("pointerout", (e) => {
      const a = e.target.closest?.("a");
      if (!a || a.contains(e.relatedTarget)) return;
      clearTimeout(showTimer);
      if (pop.contains(e.relatedTarget)) return;
      hideTimer = setTimeout(hide, HIDE_DELAY);
    });
    pop.addEventListener("pointerenter", () => clearTimeout(hideTimer));
    pop.addEventListener("pointerleave", () => { hideTimer = setTimeout(hide, HIDE_DELAY); });
    document.addEventListener("click", (e) => {
      const a = e.target.closest?.("a");
      if (!a) return;
      clearTimeout(showTimer); hide();
      // 双栏模式下 #doc-root 是独立滚动容器，页内锚点用 scrollIntoView 平滑跳转
      const href = hrefOf(a);
      if (href.startsWith("#") && href.length > 1 && !(e.ctrlKey || e.metaKey)) {
        const id = decodeURIComponent(href.slice(1));
        const target = document.getElementById(id);
        if (target && getDocPane().contains(target)) {
          e.preventDefault();
          target.scrollIntoView({ behavior: "auto", block: "start" });
          history.replaceState(null, "", `#${id}`);
        }
      }
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") hide();
      if (e.altKey && !e.ctrlKey && !e.metaKey && e.code === "KeyT") {
        e.preventDefault();
        toggleDrawer();
      }
    });
    const onScrollHide = () => { if (current && !pop.matches(":hover")) hide(); };
    window.addEventListener("scroll", onScrollHide, { passive: true });
    getDocPane().addEventListener("scroll", onScrollHide, { passive: true });
  }

