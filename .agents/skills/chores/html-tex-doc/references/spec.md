# HTML / 受控 Markdown + TeX 混合无页排版规范细则

## 设计分工与三层解耦边界

- 流式长卷与唯一编号源：HTML + MathJax 负责正文、章节、公式、图表、算法与定理的全局流式排版与顺序编号，彻底消除纸质断页留白与浮动体漂移。
- 局部高难图形与伪代码独立矢量化：TikZ 图与 `algpseudocode` / `algorithm2e` 算法框各自作为独立 `standalone` `.tex` 编译为矢量 SVG 内联进 HTML，仅对变更过的单元做增量重编（缓存键为图源、公共导言文件与该图 `\cref` 引用到的编号的内容哈希，不看文件修改时间）。
- 三层架构解耦：
  - `scripts/`（通用引擎）：`html_tex_doc.py` 是薄入口（`init` / `build` / `serve`），实现在 `scripts/htd/` 包内：`workspace`（`main.md` 前置块与论文库自动发现）、`numbering`（编号）、`texfig`（出图与内容哈希缓存）、`svgtheme`、`toc`、`render`、`build`、`assets`（运行时资源打包）、`mdsyntax` / `mdinline` / `mdconv`（受控 Markdown 与单层 `include`）、`bib`、`mathpre`（公式预渲染）、`cli`，以及 `server/`（`files`、`wal`、`search`、`watch`、`project`、`http`）；不含任何特定学校 `.cls` 硬编码。`scripts/tests/` 为测试，`scripts/perf/` 为性能测量工具。
  - `assets/`（运行时资源，不复制进工程）：`css/`（`00_tokens.css` 是唯一出现颜色、字体栈、圆角、层级字面量的文件，其余分层含 `css/shell/60_shell.css` 只引用变量）、`js/core.js`（共用小工具、路由前缀 `HTD.api` 与按论文前缀隔离的 `HTD.store`）、`js/reader/`、`js/editor/`、`js/shell/`；构建与服务按文件名顺序拼接为 `style.css` / `reader.js` / `editor.js` / `shell.css` / `shell.js`。工程可用 `src/theme.css`（覆盖变量）与 `src/extra.css`（追加规则）定制；旧工程里整份的 `src/style.css` 等仍被尊重。
  - `references/templates/`（预设空白骨架，只含内容）：`src/`（`basic` 单文件 HTML 骨架与公共 `common.tex`、`algcommon.tex`、`macros.tex`）与 `academic-md/src/`（多章受控 Markdown + `refs.bib` + `alg2e.tex` 骨架）。
  - `references/examples/`（双范式参考案例）：`linked-list/`（无外部 `.cls` 的原生算法笔记）与 `hithesis-adapter/`（外部 LaTeX `.cls` 学位论文通过项目侧薄脚本 `import_tex.py` 单向导出受控 Markdown 的接入范式）。

## 双输入源语法

构建器按 `src/` 目录内容自动选择输入管线：优先读取 `src/main.md`（解析前置块 `title`、`macros`、`bib` 并按 `<!--include 相对路径.md-->` 顺序拼接，支持 `chapters/*.md` 子目录与在 `main.md` 内穿插正文）；若无 `main.md` 但存在 `src/*.md`，则按文件名排序编译拼接；否则读取 `src/doc.html`。

### 受控学术 Markdown 语法（`src/main.md` 与 `src/*.md`）

| 语法元素 | 写法示例 | 编译产物与说明 |
| --- | --- | --- |
| 工作区入口与包含 | `src/main.md` 顶部 `---` 前置块（`title`、`macros`、`bib`、可选 `bib_order: file`）+ `<!--include 01_绪论.md-->` | 单层按序包含（禁止越界、自包含与嵌套 `include`），保留各文件独立源码行号锚点；`bib_order: file` 保留 `.bib` 原始文献序号并自动合并连续区间为 `[2–7]` |
| 文档标题（旧式） | `<!-- title: 文档标题 -->` | 无 `main.md` 前置块 `title` 时的回退页面 `<title>` |
| 自动目录、文献与脚注 | `<!--TOC-->`、`<!--REFS-->`、`<!--FOOTNOTES-->` | 分别展开为可折叠三级目录卡片、`<ol class="refs">` 文献列表与 `<section class="footnotes">` 文末双向跳转脚注 |
| 章节标题 | `# 章 {#sec:ch1}`、`## 节 {#sec:s1}`、`### 小节`、`#### 四级标题` | `#`~`###` 自动转为 `<h2>`~`<h4>`（`<h2>`/`<h3>` 自动编号并进入目录，`{#key}` 可选） |
| 无编号大节标题 | `<p class="h2">摘要</p>` | 保持章节字号与底边线，但不参与章节计数 |
| 行内样式与公式 | `*斜体*`、`**加粗**`、`` `代码` ``、`$x_k$`；独占行 `$$ {#eq:ssm}` ... `$$` | 带 `{#eq:...}` 自动注入 `\tag{n}` 并登记可引用编号；无标签则输出 `\[ ... \]` |
| 定理、问题、评注与算例 | `::: 定理 {#thm:1a num=1-a} 简称` ... `:::`；`::: 评注 {#rem:a num=(a)}`；`::: 证明` | 支持 `num=...` 显式非整数编号且不递增同类计数器；`定理`/`问题` 为浅底色主卡片，`评注`/`算例` 自动套用 `thm--remark`/`thm--example` 无底色细左线轻量样式 |
| 正文交叉引用与脚注角标 | `{@eq:ssm}`、`{@eq:ssm\|n}`、`{@sec:k10\|校勘记 K-10}`、`[^1]` | 三态编译期校验引用与脚注角标均生成 `.xref` 双向锚点，支持实时悬停预览卡片 |
| 管道表格与编号表 | 标准 Markdown `\| 列1 \| 列2 \|`（自动保护单元格内公式与交叉引用竖线）；有编号表外包 `<figure class="tbl" data-label="tab:1">` | 生成带逐行 `data-file`/`data-l` 对齐锚点的 `<table>` |
| BibTeX 文献引用 | `[@kalman1960,daum2010]` | 读取 `src/refs.bib`，合并连续序号为 `[1–3]` 并链接至 `#ref-key` |
| 原生图表与算法块 | `<figure class="alg" data-label="alg:x" data-tex="algs/x.tex">...<!--TEX--></figure>` | 原样透传 HTML 块，内部 `$...$`、`{@key}` 与 `[@cite]` 依然正常解析 |

### 原生 HTML 语法（`src/doc.html`）

- 章节 `<h2 data-label="sec:x">`、公式 `<div class="eq" data-label="eq:x">\[ ... \]</div>`、图表 `<figure class="fig|alg" data-label="..." data-tex="figs/x.tex"><!--TEX--><figcaption>...</figcaption></figure>`、表格 `<figure class="tbl" data-label="tab:x">`、命题 `<div class="thm" data-kind="命题" data-label="prop:x" data-title="简称">` 均使用 HTML 文档出现顺序作为唯一编号源。
- 论文版式硬规范：正文内不插入 `<!--TOC-->` 内联目录卡（由右上角 `☰ 目录` 抽屉统一承担）；摘要前须显式写出 `<p class="h2">摘要</p>`（英文版 `<p class="h2">Abstract</p>`）；译校、符号对照、数值复现与审核细节统一置于文末附录，不得放在摘要与正文引言之间。

## TeX 侧共享宏与反向交叉引用

- 共享数学宏 `src/macros.tex`：使用 `\newcommand{\name}[n]{body}` 维护 LaTeX 与 MathJax 共用宏；TeX 侧经 `\input{common}` 自动引入，HTML 侧注入 `window.MathJax.tex.macros`。
- TeX 内部引用 HTML 编号 `\cref{key}`：构建器扫描全文生成 `build/labels.tex`（`\lbl{key}{显示名}{anchor-id}`）；`figs/*.tex` 或 `algs/*.tex` 中调用 `\cref{key}` 时由 `common.tex` 写入 `\special{html:<a href="#anchor-id">}`，经 `xelatex -no-pdf` + `dvisvgm` 保留为 SVG 内嵌超链接。
- 深色自适应改色：TeX 图形仅需使用纯黑、`black!k` 灰阶、纯白与预定义 `accent`（`#1F6FB2`），构建器自动改写为 `currentColor` + 透明度、`var(--bg)` 与 `var(--accent)`。

## 公式预渲染与缓存（`htd/mathpre.py` + `math_prerender.mjs`）

- 时机：`build_project` 在编号、出图完成后，对正文 HTML 中的 `\(...\)` 与 `\[...\]` 做预渲染（跳过 `code`、`pre`、`script`、`style`、内联 `svg`），输出与浏览器内 MathJax 相同的 `<mjx-container jax="CHTML">` 标记；页面内嵌样式表，不再加载 MathJax 运行时。
- 缓存键：`SHA-256(mathjax-full 版本, 输出配置, macros.tex 解析出的宏, 行内/行间, 公式源码)`，一个键一个文件，位于 `<build>/mathcache/`；样式表按前三项另存为 `css-<键>.css`。键的任一成分变化即不命中，不依赖文件修改时间；全部命中时不启动 Node。
- 自足性：每条公式独立转换；样式表关闭“按用到的字形裁剪”（`adaptiveCSS: false`），因此命中缓存的公式不会缺样式，全量重算与全部命中两次产物逐字节一致。
- 字号：浏览器内 MathJax 会按正文字体的 x 高度缩放公式，构建期不知道读者的字体，故样式里用 `var(--mjx-scale)`，由 `<main>` 之前的一行内联脚本量一次后写入；容器另带 `position: relative`，与浏览器内输出一致。
- 回退：未找到 `node` 或未安装 `scripts/node_modules/mathjax-full` 时自动改用浏览器内 MathJax（CDN），构建日志会注明原因；`HTD_MATH` 取 `auto`（默认）、`browser`、`prerender`。
- 热补丁：`/__raw` 返回的已是预渲染后的正文，`editor.js` 按顶层块替换即可；仅在回退模式下才调用 `MathJax.typesetPromise`。
- 已知差异：预渲染页面没有 MathJax 的公式右键菜单；取公式源码请用 `Ctrl+Click` 反向定位。TeX 语法错误的公式在页面内以 MathJax 的报错标记显示，构建日志给出数量。

## 目录折叠与阅读器机制（`assets/js/reader/`）

- 容器隔离契约：全部文档块包裹于 `<main id="doc-root" class="doc-pane">`，阅读器与编辑器浮层挂载于 `document.body` 顶层，互不污染子节点索引，保证热更新按块精确 diff。
- 内联目录卡（`#doc-toc`）：支持点击标题栏整卡折叠/展开、`收起子节` / `展开全部` 一键切换，以及各章独立三角折叠按钮，折叠状态持久化于 `localStorage("reader.toc.collapsed")`。
- 浮动目录抽屉（`☰ 目录` / `Alt+T`）：右上角常驻目录按钮，任意滚动位置一键展开侧边目录，内置章节关键字实时过滤框与 `IntersectionObserver` 当前阅读小节高亮（ScrollSpy）。
- 栏宽与悬停预览：单栏模式下左右边缘拖拽无级调节 `--measure` 栏宽（双击或点 `↔ 宽度` 复位）；鼠标悬停于交叉引用、文献角标或 SVG 内部链接 0.28 秒弹出实时目标预览卡片。

## Web 双栏工作台与双向高亮对齐（`htd/server/` + `assets/js/editor/`）

### 本地服务接口（仅 `127.0.0.1`）

| 端点 | 方法 | 用途 |
| --- | --- | --- |
| `/__live?v=<ver>` | `GET` | 长轮询推送最新构建版本号 `v`、变更文件列表 `changed` 与编译错误 `err` |
| `/__raw` | `GET` | 返回最新 `#doc-root` 内部 HTML（公式已预渲染）供前端按顶层块 diff 替换 |
| `/__api/files` | `GET` | 列出 `src/` 下可编辑源码文件（`*.md`、`doc.html`、`macros.tex`、`refs.bib`、`algs/*.tex`、`figs/*.tex`）与 `mtime_ns` |
| `/__api/file?path=...` | `GET` / `PUT` | 读取或原子写回指定源码文件；`PUT` 校验 `base_mtime_ns`，若外部 IDE 已改盘则返回 `409 Conflict` 防止静默覆盖，写盘后通过 `threading.Event` 零延迟唤醒增量重编 |
| `/__api/search?q=...` | `GET` | 跨文件全文/大小写/正则搜索，返回文件、行号、列区间与上下文摘要 |
| `/__api/papers` | `GET` / `POST` | （仅 `--library` 模式）动态列出两层目录内发现的全部论文及驻留状态，或用 `academic-md` 模板新建论文目录并立即启动 |
| `/p/<slug>/...` | `GET` / `PUT` / `POST` | （仅 `--library` 模式）单篇论文隔离路由前缀；首次访问时惰性触发构建与文件监听，内存中注入 `__HTD_BASE__` 与 `__HTD_PAPER__` 而保持磁盘 `index.html` 纯净 |

### 双层 SyncMap 源码对齐协议与快捷键

- 编译期双层锚点：
  - 块级锚点：`<h2..h4>`、`<p>`、`<li>`、`<tr>`、`<div class="eq|thm|proof">`、`<figure>` 自动携带 `data-file`、`data-l1`、`data-l2`（图与算法额外带 `data-tex`）。
  - 行级锚点：`htd/mdinline.py` 在段落与列表项换行处自动包裹 `<span class="sl" data-file="..." data-l="N">`，使多行源码段落在浏览器渲染流中具备逐行 DOM 映射；单行超长自然段则结合 `caretRangeFromPoint` 文本片段探测精确定位字符列。
- 交互组合键：
  - `◫ 双栏` 或 `Ctrl+\`（macOS 为 `Cmd+\`）：开合左源码右渲染分屏工作台，中间分隔条支持拖拽调宽。
  - 反向同步（右渲染 → 左源码）：按住 `Ctrl`/`Cmd` 悬停右侧正文实时显示虚线瞄准框与 `文件 : 行号` 浮标；`Ctrl+Click`（或 `Alt+Click`）任意正文句、公式、定理、表格行即自动展开左栏、切换对应文件、滚动至目标行并触发双端脉冲高亮。在算法/TikZ 图上 `Ctrl+Click` 直接打开对应 `.tex` 源码，按 `Ctrl+Shift+Click` 则跳回 `.md` / `.html` 调用处。
  - 正向同步（左源码 → 右渲染）：在左侧编辑器 `Ctrl+Click`（或 `Alt+Click`）、点击左侧行号槽，或按 `Ctrl+Alt+J` / `Alt+Enter`，右侧渲染区平滑滚动至对应行级 `<span class="sl">` 或最近块元素并双端高亮；开启工具栏 `🔗 联动` 后支持光标移动静默指示对侧段落。
  - 搜索与保存：`Ctrl+F` 页内搜索（高亮命中行，支持 `Aa` 与 `.*`），`Ctrl+Shift+F` 跨文件全局搜索面板，`Ctrl+S` 立即保存（默认开启 360ms 防抖自动保存，可切换手动模式）。
