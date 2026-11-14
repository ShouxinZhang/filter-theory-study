# HTML + TeX 混合无页排版规范细则

## 1. 设计分工

- **HTML + MathJax 负责流式长卷与全局编号**：消除纸质页面高度限制、断页留白与浮动体乱飞；章节、公式、图、算法、表格、定理全部以 HTML 文档顺序作为**唯一编号源**。
- **TeX `standalone` 负责高难度局部图形与伪代码**：TikZ 图、复杂结构框、`algpseudocode` 算法等各自作为独立 `standalone` `.tex` 编译为矢量 SVG 内联进 HTML，享受完整 TeX Live 宏包生态且只对变更过的图做增量重编。

## 2. `src/doc.html` 标签与引用语法

- **文档标题**：顶部注释 `<!-- title: 文档标题 -->` 决定 `<title>`。
- **自动目录**：在需要插入目录的位置放置 `<!--TOC-->`，按 `<h2>`/`<h3>` 层级自动生成带跳转的目录卡片。
- **可编号对象**（均通过 `data-label="key"` 声明唯一标识）：
  - **章节**：`<h2 data-label="sec:xxx">标题</h2>`、`<h3 data-label="sec:yyy">子标题</h3>`（未写 `data-label` 的章节也会自动编号）。
  - **行间公式**：
    ```html
    <div class="eq" data-label="eq:cost">
    \[ T(n) = \Theta(1). \]
    </div>
    ```
    构建器自动在 `\]` 前注入 `\tag{n}`，交由 MathJax 右对齐渲染。
  - **TikZ 图与算法框**（`class="fig"` 或 `class="alg"`，通过 `data-tex` 指定相对 `src/` 的 `.tex` 路径，并在插入位置写 `<!--TEX-->` 占位注释）：
    ```html
    <figure class="fig" data-label="fig:demo" data-tex="figs/demo.tex">
      <!--TEX-->
      <figcaption>图注内容（构建器自动前置“图 n”）。</figcaption>
    </figure>
    ```
  - **表格**：`<figure class="tbl" data-label="tab:xxx"><figcaption>表题</figcaption><table>...</table></figure>`。
  - **定理/命题/定义**：`<div class="thm" data-kind="命题" data-label="prop:xxx" data-title="可选简称"><p>正文</p></div>`，紧随其后的 `<div class="proof">` 在悬停预览时会一并展示。
- **正文交叉引用**：
  - `{@key}`：渲染为带页内锚点跳转的完整名称（如 `第 2 节`、`式 (3)`、`图 1`、`算法 2`、`命题 1`、`表 1`）。
  - `{@key|n}`：仅输出纯编号（如 `3`、`2.1`）。

## 3. TeX 侧共享宏与反向交叉引用

- **共享数学宏 `src/macros.tex`**：
  - 仅使用 `\newcommand{\name}[n]{body}` 形式，且 `body` 必须同时被 LaTeX 与 MathJax 支持。
  - TeX 侧通过 `\input{common}` 自动加载 `macros.tex`；HTML 侧由 `html_tex_doc.py` 解析并注入 `window.MathJax.tex.macros`，两边严格同源。
- **TeX 内部引用 HTML 编号 `\cref{key}`**：
  - 构建器先扫描 `doc.html` 生成 `build/labels.tex`（形如 `\lbl{eq:cost}{式~(3)}{eq-cost}`）。
  - 在任何 `figs/*.tex` 或 `algs/*.tex` 中直接写 `\cref{eq:cost}` 或 `\cref{alg:insert}`，`common.tex` 会将其渲染为带强调色与 `\special{html:<a href="#eq-cost">}` 的超链接，`dvisvgm` 将其保留为 SVG `<a>` 节点。
  - 构建器默认在命令行前置 `\def\pgfsysdriver{pgfsys-dvisvgm.def}` 调用 `xelatex -no-pdf`，确保 TikZ 绘图指令完整进入 `.xdv`。

## 4. 深色主题改色与阅读器机制

- **SVG 主题自适应改色（`theme_colors`）**：
  - TeX 中使用纯黑、`black!k` 灰阶、纯白填充与预定义的 `accent` 色（`#1F6FB2`）即可，无需手写深色分支。
  - 构建内联时自动将灰阶转为 `currentColor` + 对应不透明度（保持明暗层次且深色下柔和不刺眼），纯白转为 `var(--bg)`，`accent` 转为 `var(--accent)`。
- **内置阅读器（`reader.js` + `style.css`）**：
  - **栏宽**：默认响应式自适应；正文左右两侧边缘支持拖拽无级调节宽度（实时显示像素与每行字数，持久化至 `localStorage`），双击边缘或点右上角 `↔ 宽度` 复位。
  - **主题**：右上角按钮支持 `◐ 自动 / ☀ 浅色 / ☾ 深色` 循环切换，首帧前注入防闪烁脚本。
  - **悬停预览**：鼠标停留在正文链接或 SVG 内部链接上 0.28 秒即弹出目标块实时副本（含 MathJax 公式与 SVG 图），支持移入滚动、内部二次点击与 `Esc` 关闭。

## 5. 构建门禁与已知边界

- **强门禁**：HTML 侧未定义 `{@key}`、TeX 侧未定义 `\cref{key}`、重复 `data-label`、缺失 `<!--TEX-->` 或 TeX 编译报错时，`html_tex_doc.py build` 均返回非 0 退出码并列出全部错误。
- **已知边界**：
  - `dvisvgm` 采用 `--no-fonts` 将图内字形转为矢量路径，跨平台零字体缺失风险，但 SVG 图内文字不支持直接鼠标涂抹选中。
  - MathJax 默认引用 jsDelivr CDN，完全离线环境可将脚本地址替换为本地 MathJax 副本。
