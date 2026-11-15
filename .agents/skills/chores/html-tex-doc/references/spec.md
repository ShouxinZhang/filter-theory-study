# HTML / 受控 Markdown + TeX 混合无页排版规范细则

## 设计分工与三层解耦边界

- 流式长卷与唯一编号源：HTML + MathJax 负责正文、章节、公式、图表、算法与定理的全局流式排版与顺序编号，彻底消除纸质断页留白与浮动体漂移。
- 局部高难图形与伪代码独立矢量化：TikZ 图与 `algpseudocode` / `algorithm2e` 算法框各自作为独立 `standalone` `.tex` 编译为矢量 SVG 内联进 HTML，仅对变更过的单元做增量重编。
- 三层架构解耦：
  - `scripts/`（通用引擎）：`html_tex_doc.py`（`init` / `build` / `serve`）、`md_conv.py`（受控学术 Markdown 与 BibTeX 编译及行级源码锚点注入）、`dev_server.py`（长轮询热重载与双栏编辑 REST 服务），不含任何特定学校 `.cls` 硬编码。
  - `references/templates/`（预设空白骨架）：`src/`（`basic` 单文件 HTML 骨架，同时承载公共 `common.tex`、`style.css`、`reader.js`、`editor.js`）与 `academic-md/src/`（多章受控 Markdown + `refs.bib` + `alg2e.tex` 骨架）。
  - `references/examples/`（双范式参考案例）：`linked-list/`（无外部 `.cls` 的原生算法笔记）与 `hithesis-adapter/`（外部 LaTeX `.cls` 学位论文通过项目侧薄脚本 `import_tex.py` 单向导出受控 Markdown 的接入范式）。

## 双输入源语法

构建器按 `src/` 目录内容自动选择输入管线：若存在 `src/*.md` 则按文件名排序编译拼接（支持 `src/refs.bib` 文献库与 `src/figs/*.svg` 静态图同步），否则读取 `src/doc.html`。

### 受控学术 Markdown 语法（`src/*.md`）

| 语法元素 | 写法示例 | 编译产物与说明 |
| --- | --- | --- |
| 文档标题 | `<!-- title: 文档标题 -->` | 决定页面 `<title>` |
| 自动目录与文献表 | `<!--TOC-->`、`<!--REFS-->` | 分别展开为可折叠三级目录卡片与按首次引用顺序排列的 `<ol class="refs">` |
| 章节标题 | `# 章 {#sec:ch1}`、`## 节 {#sec:s1}`、`### 小节`、`#### 四级标题` | `#`~`###` 自动转为 `<h2>`~`<h4>`（`<h2>`/`<h3>` 自动编号并进入目录，`{#key}` 可选） |
| 无编号大节标题 | `<p class="h2">摘要</p>` | 保持章节字号与底边线，但不参与章节计数 |
| 行内与行间公式 | `$x_k$`；独占行 `$$ {#eq:ssm}` ... `$$` | 带 `{#eq:...}` 自动注入 `\tag{n}` 并登记可引用编号；无标签则输出 `\[ ... \]` |
| 定理与证明块 | `::: 定理 {#thm:main} 可选简称` ... `:::`；`::: 证明` ... `:::` | 生成 `<div class="thm">` 与带右对齐 `□` 的 `<div class="proof">`，支持块内嵌套编号公式 |
| 正文交叉引用 | `{@eq:ssm}`、`{@eq:ssm\|n}` | 分别渲染为带锚点与悬停预览的完整名称（如 `式 (1)`、`算法 1`）或纯编号 `1` |
| BibTeX 文献引用 | `[@kalman1960,daum2010]` | 读取 `src/refs.bib`，合并连续序号为 `[1–3]` 并链接至 `#ref-key` |
| 原生图表与算法块 | `<figure class="alg" data-label="alg:x" data-tex="algs/x.tex">...<!--TEX--></figure>` | 原样透传 HTML 块，内部 `$...$`、`{@key}` 与 `[@cite]` 依然正常解析 |

### 原生 HTML 语法（`src/doc.html`）

- 章节 `<h2 data-label="sec:x">`、公式 `<div class="eq" data-label="eq:x">\[ ... \]</div>`、图表 `<figure class="fig|alg" data-label="..." data-tex="figs/x.tex"><!--TEX--><figcaption>...</figcaption></figure>`、表格 `<figure class="tbl" data-label="tab:x">`、命题 `<div class="thm" data-kind="命题" data-label="prop:x" data-title="简称">` 均使用 HTML 文档出现顺序作为唯一编号源。

## TeX 侧共享宏与反向交叉引用

- 共享数学宏 `src/macros.tex`：使用 `\newcommand{\name}[n]{body}` 维护 LaTeX 与 MathJax 共用宏；TeX 侧经 `\input{common}` 自动引入，HTML 侧注入 `window.MathJax.tex.macros`。
- TeX 内部引用 HTML 编号 `\cref{key}`：构建器扫描全文生成 `build/labels.tex`（`\lbl{key}{显示名}{anchor-id}`）；`figs/*.tex` 或 `algs/*.tex` 中调用 `\cref{key}` 时由 `common.tex` 写入 `\special{html:<a href="#anchor-id">}`，经 `xelatex -no-pdf` + `dvisvgm` 保留为 SVG 内嵌超链接。
- 深色自适应改色：TeX 图形仅需使用纯黑、`black!k` 灰阶、纯白与预定义 `accent`（`#1F6FB2`），构建器自动改写为 `currentColor` + 透明度、`var(--bg)` 与 `var(--accent)`。

## 目录折叠与阅读器机制（`reader.js`）

- 容器隔离契约：全部文档块包裹于 `<main id="doc-root" class="doc-pane">`，阅读器与编辑器浮层挂载于 `document.body` 顶层，互不污染子节点索引，保证热更新按块精确 diff。
- 内联目录卡（`#doc-toc`）：支持点击标题栏整卡折叠/展开、`收起子节` / `展开全部` 一键切换，以及各章独立三角折叠按钮，折叠状态持久化于 `localStorage("reader.toc.collapsed")`。
- 浮动目录抽屉（`☰ 目录` / `Alt+T`）：右上角常驻目录按钮，任意滚动位置一键展开侧边目录，内置章节关键字实时过滤框与 `IntersectionObserver` 当前阅读小节高亮（ScrollSpy）。
- 栏宽与悬停预览：单栏模式下左右边缘拖拽无级调节 `--measure` 栏宽（双击或点 `↔ 宽度` 复位）；鼠标悬停于交叉引用、文献角标或 SVG 内部链接 0.28 秒弹出实时目标预览卡片。

## Web 双栏工作台与双向高亮对齐（`dev_server.py` + `editor.js`）

### 本地服务接口（仅 `127.0.0.1`）

| 端点 | 方法 | 用途 |
| --- | --- | --- |
| `/__live?v=<ver>` | `GET` | 长轮询推送最新构建版本号 `v`、变更文件列表 `changed` 与编译错误 `err` |
| `/__raw` | `GET` | 返回最新 `#doc-root` 内部 HTML 供前端按顶层块 diff + MathJax 局部重排 |
| `/__api/files` | `GET` | 列出 `src/` 下可编辑源码文件（`*.md`、`doc.html`、`macros.tex`、`refs.bib`、`algs/*.tex`、`figs/*.tex`）与 `mtime_ns` |
| `/__api/file?path=...` | `GET` / `PUT` | 读取或原子写回指定源码文件；`PUT` 校验 `base_mtime_ns`，若外部 IDE 已改盘则返回 `409 Conflict` 防止静默覆盖，写盘后通过 `threading.Event` 零延迟唤醒增量重编 |
| `/__api/search?q=...` | `GET` | 跨文件全文/大小写/正则搜索，返回文件、行号、列区间与上下文摘要 |

### 双层 SyncMap 源码对齐协议与快捷键

- 编译期双层锚点：
  - 块级锚点：`<h2..h4>`、`<p>`、`<li>`、`<tr>`、`<div class="eq|thm|proof">`、`<figure>` 自动携带 `data-file`、`data-l1`、`data-l2`（图与算法额外带 `data-tex`）。
  - 行级锚点：`md_conv.py` 在段落与列表项换行处自动包裹 `<span class="sl" data-file="..." data-l="N">`，使多行源码段落在浏览器渲染流中具备逐行 DOM 映射；单行超长自然段则结合 `caretRangeFromPoint` 文本片段探测精确定位字符列。
- 交互组合键：
  - `◫ 双栏` 或 `Ctrl+\`（macOS 为 `Cmd+\`）：开合左源码右渲染分屏工作台，中间分隔条支持拖拽调宽。
  - 反向同步（右渲染 → 左源码）：按住 `Ctrl`/`Cmd` 悬停右侧正文实时显示虚线瞄准框与 `文件 : 行号` 浮标；`Ctrl+Click`（或 `Alt+Click`）任意正文句、公式、定理、表格行即自动展开左栏、切换对应文件、滚动至目标行并触发双端脉冲高亮。在算法/TikZ 图上 `Ctrl+Click` 直接打开对应 `.tex` 源码，按 `Ctrl+Shift+Click` 则跳回 `.md` / `.html` 调用处。
  - 正向同步（左源码 → 右渲染）：在左侧编辑器 `Ctrl+Click`（或 `Alt+Click`）、点击左侧行号槽，或按 `Ctrl+Alt+J` / `Alt+Enter`，右侧渲染区平滑滚动至对应行级 `<span class="sl">` 或最近块元素并双端高亮；开启工具栏 `🔗 联动` 后支持光标移动静默指示对侧段落。
  - 搜索与保存：`Ctrl+F` 页内搜索（高亮命中行，支持 `Aa` 与 `.*`），`Ctrl+Shift+F` 跨文件全局搜索面板，`Ctrl+S` 立即保存（默认开启 360ms 防抖自动保存，可切换手动模式）。
