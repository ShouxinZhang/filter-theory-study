---
name: html-tex-doc
description: 无分页 HTML 正文 + TeX standalone 出图/算法的混合排版工作流：唯一编号源、SVG 内嵌超链接、深色主题自动改色、栏宽拖拽与链接悬停预览。
---

# html-tex-doc

用流式无分页 HTML + MathJax 编写正文与公式，用 TeX `standalone` 编译 TikZ 图与 `algpseudocode` 算法框为内联 SVG，统一编号、双向超链接与深色主题。

## 速查

```bash
S=.agents/skills/chores/html-tex-doc/scripts/html_tex_doc.py

# 1. 初始化混合文档工程骨架（生成 <dir>/src/）
python3 $S init <dir> --title "文档标题"

# 2. 增量构建单页站点（默认读 <dir>/src，输出 <dir>/outputs/site）
python3 $S build <dir>

# 3. 显式指定源码/缓存/输出路径（如编译内置示例到临时目录）
python3 $S build --src <src_dir> --build-dir <build_dir> --out <site_dir> [--force]

# 4. 本地 HTTP 预览
python3 -m http.server 18767 --bind 127.0.0.1 -d <dir>/outputs/site
```

## 核心流程

1. **编辑正文与宏**：在 `src/macros.tex` 维护同源 `\newcommand`；在 `src/doc.html` 用 `data-label` 标记章节/公式/图表/命题，用 `{@key}` 引用。
2. **编写 TeX 图/算法**：在 `src/figs/*.tex` 或 `src/algs/*.tex` 中 `\input{common}`，通过 `\cref{key}` 引用 HTML 编号（自动生成 SVG 页内超链接），并在 `doc.html` 对应 `<figure data-tex="...">` 内放 `<!--TEX-->` 占位注释。
3. **构建与门禁核验**：运行 `html_tex_doc.py build`，自动完成唯一编号、`labels.tex` 生成、`xelatex` + `dvisvgm` 矢量编译、深色自适应改色及未定义引用检查。

## 参考

- [references/spec.md](references/spec.md): 标签语法、共享宏、`\cref` 机制、深色改色与阅读器细则.
- [references/templates/src/](references/templates/src/): `init` 使用的可复用空白工程骨架（含 `reader.js` 与 `style.css`）.
- [references/examples/linked-list/README.md](references/examples/linked-list/README.md): 《链表：结构、操作与复杂度》完整示例源码与编译命令.
