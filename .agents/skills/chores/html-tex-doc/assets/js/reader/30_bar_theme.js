  /* ---------------- 3. 主题与右上角工具条（单色线性 SVG 图标） ---------------- */
  const SVG_TOC = ico('<path d="M2.5 4h11M2.5 8h8M2.5 12h11"/>');
  const SVG_MEASURE = ico('<path d="M2 8h12M4.5 5.5 2 8l2.5 2.5M11.5 5.5 14 8l-2.5 2.5"/>');
  const THEMES = ["auto", "light", "dark"];
  const THEME_LABEL = {
    auto: `${ico('<circle cx="8" cy="8" r="5.5"/><path d="M8 2.5v11a5.5 5.5 0 0 0 0-11z" fill="currentColor" stroke="none"/>')}<span>自动</span>`,
    light: `${ico('<circle cx="8" cy="8" r="3"/><path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1.1 1.1M11.5 11.5l1.1 1.1M12.6 3.4l-1.1 1.1M4.5 11.5l-1.1 1.1"/>')}<span>浅色</span>`,
    dark: `${ico('<path d="M13 9.8A5.5 5.5 0 0 1 6.2 3 5.5 5.5 0 1 0 13 9.8Z"/>')}<span>深色</span>`,
  };
  const applyTheme = (t) => { t === "auto" ? root.removeAttribute("data-theme") : root.setAttribute("data-theme", t); };
  let theme = THEMES.includes(store.get("reader.theme")) ? store.get("reader.theme") : "auto";
  applyTheme(theme);

  function setupBar() {
    const bar = document.createElement("div");
    bar.className = "reader-bar ui-bar ui-bar--float";
    bar.id = "reader-bar";

    tocBtn = document.createElement("button");
    tocBtn.type = "button";
    tocBtn.dataset.role = "toc";
    tocBtn.innerHTML = `${SVG_TOC}<span>目录</span>`;
    tocBtn.title = "展开或收起浮动章节目录（快捷键 Alt+T）";
    tocBtn.onclick = () => toggleDrawer();

    const tBtn = document.createElement("button");
    tBtn.type = "button";
    tBtn.dataset.role = "theme";
    tBtn.innerHTML = THEME_LABEL[theme];
    tBtn.title = "切换主题：自动（跟随系统）/ 浅色 / 深色";
    tBtn.onclick = () => {
      theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
      applyTheme(theme); store.set("reader.theme", theme); tBtn.innerHTML = THEME_LABEL[theme];
    };

    const wBtn = document.createElement("button");
    wBtn.type = "button";
    wBtn.dataset.role = "measure";
    wBtn.innerHTML = `${SVG_MEASURE}<span>宽度</span>`;
    wBtn.title = "恢复自适应栏宽（也可拖拽正文两侧边缘调整）";
    wBtn.onclick = resetMeasure;

    for (const b of [tocBtn, tBtn, wBtn]) b.className = "ui-btn";
    bar.append(tocBtn, tBtn, wBtn);
    document.body.appendChild(bar);
  }

