  /* ---------------- 2. 目录单独折叠（文内卡片 + 浮动抽屉） ---------------- */
  let drawer, drawerBody, drawerFilter, tocBtn;

  function jumpToHeading(id, e) {
    const target = document.getElementById(id);
    if (!target) return;
    target.scrollIntoView({ behavior: "auto", block: "start" });
    target.classList.remove("toc-jumped");
    void target.offsetWidth;
    target.classList.add("toc-jumped");
    if (e && (e.ctrlKey || e.metaKey || e.altKey)) {
      window.dispatchEvent(new CustomEvent("toc:ctrl-jump", { detail: { target } }));
    }
  }

  function wireTocTree(container) {
    if (!container) return;
    if (!container.dataset.itemWired) {
      container.dataset.itemWired = "1";
      container.addEventListener("click", (e) => {
        const item = e.target.closest?.(".toc-item[data-target]");
        if (!item || !container.contains(item)) return;
        e.preventDefault();
        e.stopPropagation();
        jumpToHeading(item.dataset.target, e);
        if (container.closest(".toc-drawer") && window.innerWidth < 920) toggleDrawer(false);
      });
    }
    container.querySelectorAll(".toc-caret").forEach((btn) => {
      if (btn.dataset.wired) return;
      btn.dataset.wired = "1";
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const li = btn.closest("li.toc-branch");
        if (!li) return;
        const folded = li.classList.toggle("is-folded");
        btn.setAttribute("aria-expanded", String(!folded));
      });
    });
    container.querySelectorAll("[data-toc-act]").forEach((btn) => {
      if (btn.dataset.wired) return;
      btn.dataset.wired = "1";
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const scope = btn.closest("nav.toc, .toc-drawer") || container;
        const fold = btn.dataset.tocAct === "fold-sub";
        scope.querySelectorAll("li.toc-branch").forEach((li) => {
          li.classList.toggle("is-folded", fold);
          const c = li.querySelector(":scope > .toc-row > .toc-caret");
          if (c) c.setAttribute("aria-expanded", String(!fold));
        });
      });
    });
  }

  function bindInlineToc() {
    const nav = document.querySelector("nav.toc");
    if (!nav) return;
    // 兼容并改造遗留静态超链接目录项为无超链接大纲按钮
    nav.querySelectorAll('a[href^="#"]').forEach((a) => {
      const id = decodeURIComponent(a.getAttribute("href").slice(1));
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "toc-item ui-row ui-row--dense";
      btn.dataset.target = id;
      btn.append(...Array.from(a.childNodes));
      a.replaceWith(btn);
    });
    // 兼容未带 .toc-head 的旧版静态目录结构
    if (!nav.querySelector(".toc-head")) {
      const ol = nav.querySelector("ol");
      const count = nav.querySelectorAll(".toc-item").length;
      const head = document.createElement("div");
      head.className = "toc-head";
      head.innerHTML = `<button type="button" class="toc-toggle" aria-expanded="true" title="点击折叠或展开目录卡片">`
        + `<span class="toc-toggle-icon">▾</span><strong>目录</strong><span class="toc-meta">共 ${count} 节</span></button>`;
      const bodyWrap = document.createElement("div");
      bodyWrap.className = "toc-body";
      if (ol) bodyWrap.appendChild(ol);
      nav.replaceChildren(head, bodyWrap);
    }
    const toggle = nav.querySelector(".toc-toggle");
    const savedCollapsed = store.get("reader.tocCollapsed") === "1";
    nav.classList.toggle("is-collapsed", savedCollapsed);
    if (toggle) {
      toggle.setAttribute("aria-expanded", String(!savedCollapsed));
      if (!toggle.dataset.wired) {
        toggle.dataset.wired = "1";
        toggle.addEventListener("click", () => {
          const collapsed = nav.classList.toggle("is-collapsed");
          toggle.setAttribute("aria-expanded", String(!collapsed));
          store.set("reader.tocCollapsed", collapsed ? "1" : "0");
        });
      }
    }
    wireTocTree(nav);
  }

  function collectHeadingsTree() {
    const pane = getDocPane();
    const heads = Array.from(pane.querySelectorAll("h2[id], h3[id], h4[id]"));
    const roots = [], stack = [];
    for (const h of heads) {
      const lv = h.tagName === "H2" ? 1 : h.tagName === "H3" ? 2 : 3;
      const numEl = h.querySelector(".secnum");
      const num = numEl ? numEl.textContent.trim() : "";
      const clone = h.cloneNode(true);
      clone.querySelector(".secnum")?.remove();
      const title = clone.textContent.trim();
      const node = { lv, id: h.id, num, title, children: [] };
      while (stack.length && stack[stack.length - 1].lv >= lv) stack.pop();
      if (stack.length) stack[stack.length - 1].children.push(node);
      else roots.push(node);
      stack.push(node);
    }
    return { roots, total: heads.length };
  }

  function renderDrawerTree() {
    if (!drawerBody) return;
    const { roots, total } = collectHeadingsTree();
    if (tocBtn) tocBtn.style.display = total ? "" : "none";
    const q = (drawerFilter?.value || "").trim().toLowerCase();

    function emit(items) {
      const ol = document.createElement("ol");
      for (const n of items) {
        const selfHit = !q || `${n.num} ${n.title}`.toLowerCase().includes(q);
        const childOl = n.children.length ? emit(n.children) : null;
        const hasChildHit = childOl && childOl.children.length > 0;
        if (!selfHit && !hasChildHit) continue;

        const li = document.createElement("li");
        li.className = n.children.length ? "toc-branch" : "toc-leaf";
        li.dataset.lv = String(n.lv);
        const row = document.createElement("div");
        row.className = "toc-row";
        row.dataset.targetId = n.id;

        if (n.children.length) {
          const caret = document.createElement("button");
          caret.type = "button";
          caret.className = "toc-caret";
          caret.textContent = "▾";
          caret.title = "折叠或展开子节";
          caret.setAttribute("aria-expanded", "true");
          row.appendChild(caret);
        } else {
          const pad = document.createElement("span");
          pad.className = "toc-caret-pad";
          row.appendChild(pad);
        }

        const item = document.createElement("button");
        item.type = "button";
        item.className = "toc-item ui-row ui-row--dense";
        item.dataset.target = n.id;
        const numSpan = document.createElement("span");
        numSpan.className = "toc-num";
        numSpan.textContent = n.num;
        const txtSpan = document.createElement("span");
        txtSpan.className = "toc-txt";
        txtSpan.textContent = n.title;
        item.append(numSpan, txtSpan);
        row.appendChild(item);
        li.appendChild(row);
        if (childOl && childOl.children.length) li.appendChild(childOl);
        ol.appendChild(li);
      }
      return ol;
    }

    drawerBody.replaceChildren(emit(roots));
    wireTocTree(drawer);
    updateScrollSpy();
  }

  function updateScrollSpy() {
    if (!drawer || !drawer.classList.contains("open")) return;
    const pane = getDocPane();
    const heads = Array.from(pane.querySelectorAll("h2[id], h3[id], h4[id]"));
    if (!heads.length) return;
    let activeId = heads[0].id;
    const threshold = 110;
    for (const h of heads) {
      if (h.getBoundingClientRect().top <= threshold) activeId = h.id;
      else break;
    }
    drawer.querySelectorAll(".toc-row.is-current").forEach((r) => r.classList.remove("is-current"));
    const cur = drawer.querySelector(`.toc-row[data-target-id="${CSS.escape(activeId)}"]`);
    if (cur) cur.classList.add("is-current");
  }

  function toggleDrawer(force) {
    if (!drawer) return;
    const next = typeof force === "boolean" ? force : !drawer.classList.contains("open");
    drawer.classList.toggle("open", next);
    if (tocBtn) tocBtn.classList.toggle("is-active", next);
    if (next) {
      renderDrawerTree();
      setTimeout(() => drawerFilter?.focus(), 20);
    }
  }

  function setupTocDrawer() {
    drawer = document.createElement("aside");
    drawer.className = "toc-drawer ui-popover";
    drawer.setAttribute("aria-label", "浮动章节目录");
    drawer.innerHTML = `<div class="toc-drawer-head ui-bar">`
      + `<input type="search" class="toc-drawer-filter ui-input" placeholder="筛选章节标题…">`
      + `<button type="button" class="toc-sub-btn ui-btn ui-btn--sm" data-toc-act="fold-sub" title="仅显示一级章">章</button>`
      + `<button type="button" class="toc-sub-btn ui-btn ui-btn--sm" data-toc-act="expand-all" title="展开全部小节">全</button>`
      + `</div><div class="toc-drawer-body"></div>`;
    document.body.appendChild(drawer);
    drawerBody = drawer.querySelector(".toc-drawer-body");
    drawerFilter = drawer.querySelector(".toc-drawer-filter");
    drawerFilter.addEventListener("input", renderDrawerTree);
    drawerFilter.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (drawerFilter.value) { drawerFilter.value = ""; renderDrawerTree(); }
        else toggleDrawer(false);
      }
    });
    wireTocTree(drawer);

    const onScroll = () => updateScrollSpy();
    window.addEventListener("scroll", onScroll, { passive: true });
    getDocPane().addEventListener("scroll", onScroll, { passive: true });
    document.addEventListener("mousedown", (e) => {
      if (drawer.classList.contains("open") && !drawer.contains(e.target) && !tocBtn?.contains(e.target)) {
        toggleDrawer(false);
      }
    });
  }

