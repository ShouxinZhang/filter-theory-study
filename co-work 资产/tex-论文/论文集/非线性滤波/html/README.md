# 论文 HTML 副本（内容优先的快速预览）

本目录是上级 TeX 论文的**独立副本**：正文为 `src/*.md`，保存后约 0.1 秒内在浏览器局部刷新。
它与 `../main.tex` 互不同步；`import_tex.py` 仅用于最初的一次性导入（重跑会覆盖 `src/`）。

## 使用

```bash
python3 thesis_html.py serve    # 打开 http://127.0.0.1:18767 ，编辑 src/*.md 保存即刷新
python3 thesis_html.py build    # 只构建一次，产物在 outputs/site/index.html
```

刷新只替换变化的段落并滚动到修改处；构建出错时页面底部显示红色错误条，正文保持上一次成功的版本。

## Markdown 约定

| 写法 | 含义 |
| --- | --- |
| `# 章 {#label}`、`## 节 {#label}`、`### 小节 {#label}` | 标题，自动编号；`{#label}` 可省 |
| `$x$`；独占一行的 `$$ {#eq:key}` … `$$` | 行内 / 行间公式；带标签才编号 |
| `{@key}`、`{@key\|n}` | 交叉引用：全称（“式 (3)”）/ 仅编号 |
| `[@key1,key2]` | 文献引用，键来自 `src/refs.bib`，按首次出现编号 |
| `::: 定理 {#label} 标题` … `:::` | 定理类（定理/命题/引理/定义…）；`::: 证明` 为证明 |
| `1. …`、`- …` | 列表（块前后空一行） |
| 以 `<figure`、`<table` 等开头的块 | 原样 HTML（图、表、算法），其中 `$…$` 与引用仍生效 |
| `<!-- … -->` | 注释，不输出 |

- 文件按文件名排序拼接；`<!--TOC-->` 为目录，`<!--REFS-->` 为参考文献表的位置。
- 算法是 `src/algs/*.tex`（algorithm2e，独立编译为 SVG，其中用 `\cref{key}` 引用正文编号）；图是 `src/figs/*.svg`。
- 数学宏写在 `src/macros.tex`，MathJax 与算法 TeX 共用。
- 编号、悬停预览、深色主题、栏宽拖拽由 `.agents/skills/chores/html-tex-doc` 构建器提供。
