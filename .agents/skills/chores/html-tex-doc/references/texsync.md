# TeX <-> 受控学术 Markdown 双向互换规范细则（`htd/texsync/`）

## 设计定位与不变量

- 零手写脚本：通过 `html_tex_doc.py` 内置子命令 `import-tex`（同义别名 `tex2html`）与 `export-tex`（同义别名 `html2tex`）统一驱动 `TeX <-> 受控学术 Markdown` 双向转换，无需在单篇论文或学位论文目录手写 `import_tex.py` / `export_tex.py`。
- 纯 Python 毫秒级运行：基于确定性花括号/方括号状态机与双层 `difflib.SequenceMatcher`（块级 + 段落句级 / 列表项级），单篇长文或整本学位论文互换耗时 `< 200 ms`，无外部 AST 进程开销。
- 核心往返恒等式：设正向解码映射为 $F: \text{TeX} \to \text{Markdown}$，最小差异补丁算子为 $G_{\text{patch}}(T, M') \to T'$，则任意合法回写必须满足内存强校验：

$$
F\bigl(G_{\text{patch}}(T, M')\bigr) \equiv M'
$$

  一旦任意目标文件触发只读结构门禁或往返不一致，整批操作保证 **0 字节落盘** 并以退出码 `1` 报告精确行号。

## CLI 子命令与参数

### `import-tex`（别名 `tex2html`）

将 LaTeX 源文件确定性导入为受控学术 Markdown，或校验双端是否零差异。

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `tex_dir` | `.` | TeX 工程根目录（若传入已含 `texsync.json` 的 HTML 目录且未指定 `-o`，自动按清单反查 `tex_root`） |
| `-o`, `--out-html` | `<tex_dir>/html` | 目标 HTML 工程目录（源码位于其下 `src/`，清单位于 `<html_dir>/texsync.json`） |
| `--check` | `False` | 逐字节校验当前 `src/*.md` 与 $F(\text{TeX})$ 是否零差异；零差异返回 `0`，有差异输出 unified diff 并返回 `1` |
| `--apply` | `False` | 原子写盘（若尚无 `texsync.json` 则自动发现 `main.tex` 结构，抽取 `src/macros.tex`、`src/refs.bib`、`src/algs/*.tex` 并生成 `src/main.md`、`src/*.md`、`.gitignore` 与 `texsync.json`） |

未传 `--check` 与 `--apply` 时为纯预览模式：仅向 `stdout` 打印 unified diff，不修改任何磁盘文件。

### `export-tex`（别名 `html2tex`）

将受控学术 Markdown 按句最小差异回写至既有 TeX 工程，或为纯 Markdown 工程一键生成可编译父级 `ctexart` 工程。

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `html_dir` | `.` | HTML 工程目录；智能路径归一：若 `<dir>/src` 不存在但 `<dir>/html/src` 存在，自动定位 `html_dir = <dir>/html` 且默认 `tex_root = <dir>` |
| `--to` | 清单 `tex_root` | 显式覆盖目标 TeX 工程根目录（`--init-tex` 未指定时：若 `html_dir` 名为 `html` 则取其父目录，否则取 `<html_dir>/tex`） |
| `--init-tex` | `False` | 从 `src/main.md`（或 `src/*.md`）与内置 `tex-article` 模板机械生成 `main.tex`、`preamble.tex`、`build.sh`、`.gitignore`、`sections/*.tex` 及 `texsync.json` |
| `-f`, `--force` | `False` | 配合 `--init-tex` 允许覆盖已存在的 `main.tex` 骨架 |
| `--apply` | `False` | 全部目标校验通过后原子落盘（默认仅打印 unified diff 或待创建文件列表预览） |

### 典型工作流

```bash
S=.agents/skills/chores/html-tex-doc/scripts/html_tex_doc.py

# 场景 A：新建受控 Markdown 论文 -> 一键生成父级 LaTeX 工程并编译 PDF
python3 $S init my-paper/html --preset academic-md --title "论文标题"
python3 $S export-tex my-paper --init-tex --apply
bash my-paper/build.sh
python3 $S import-tex my-paper --check

# 场景 B：既有 LaTeX 论文/学位论文 -> 导入 Web 双栏精修 -> 最小差异回写 TeX
python3 $S import-tex path/to/thesis --apply
python3 $S serve path/to/thesis/html --port 18767
python3 $S export-tex path/to/thesis             # 先预览 unified diff
python3 $S export-tex path/to/thesis --apply     # 校验通过后原子写回 .tex
```

## `texsync.json` 清单规范与 `SyncSpec`

清单文件固定位于 `<html_dir>/texsync.json`，结构如下：

```json
{
  "version": 1,
  "tex_root": "..",
  "main_tex": "main.tex",
  "spec": {
    "ref_templates": [["eq:", "式~\\eqref{", ""], ["thm:", "定理~\\ref{", ""]],
    "auto_envs": [["theorem", "定理"], ["corollary", "推论"], ["example", "算例"]],
    "num_envs": [["theoremn", "定理"], ["problemn", "问题"], ["remarkn", "评注"]],
    "proof_env": ["proof", "证明"],
    "bib_tex": "\\bibliography{html/src/refs}",
    "colspecs": [[2, "lX"], [3, "p{0.24\\textwidth}p{0.19\\textwidth}X"]],
    "heading_cmds": ["section", "subsection", "subsubsection"]
  },
  "pairs": [
    {
      "tex": "sections/abstract.tex",
      "md": "src/main.md",
      "md_slice": ["</header>", "<!--TOC-->"],
      "guard_main_tex": "main.tex"
    },
    {
      "tex": "sections/00_导读与符号约定.tex",
      "md": "src/00_导读与符号约定.md"
    }
  ]
}
```

- 预设规格：
  - `KALMAN_SPEC`：面向 `article` / `ctexart` 单篇论文，`heading_cmds = ("section", "subsection", "subsubsection")`。
  - `BOOK_SPEC`：面向 `book` / `ctexbook` / `hithesisbook` 学位论文或专著，`heading_cmds = ("chapter", "section", "subsection")`，额外内置 `alg:`、`prop:`、`lem:`、`def:`、`ass:`、`ch:` 引用前缀与 `proposition`、`lemma`、`definition`、`assumption`、`remark` 自动编号环境；`discover_tex_project` 还会扫描导言区 `\newtheorem` 自动补充环境表。
- 切片与主文件守卫：`md_slice: [start_marker, end_marker]` 允许将 `sections/abstract.tex` 映射至 `src/main.md` 的摘要切片区间；当同时声明 `guard_main_tex` 时，回写期校验 `main.md` 切片外的头部（前置块与 `<header>`）和尾部（`<!--TOC-->` 与 `<!--include ...-->` 列表）未被意外改动。

## 块级与行内双向语法映射对照表

### 块级单元（`parse_tex_units` / `parse_md_units`）

| 单元类别 | TeX 侧写法（$T$） | 受控 Markdown 侧写法（$M = F(T)$） | 回写策略（$G_{\text{patch}}$） |
| --- | --- | --- | --- |
| 三级章节标题 | `\section[短标题]{标题}\label{k}`（`BOOK_SPEC` 顶层为 `\chapter`） | `# 标题 {#k}`（`##`、`###` 依 `heading_cmds` 递推） | 未改时原样保留 `[短标题]`；改标题时更新主标题 |
| 无编号大节标题 | `\section*{摘要}`（`BOOK_SPEC` 为 `\chapter*{摘要}`） | `<p class="h2">摘要</p>` | 双向确定性互转 |
| 展示公式 | `\begin{equation}\label{eq:1} ... \end{equation}` / `equation*` | `$$ {#eq:1}` ... `$$` / `$$` ... `$$` | 保持紧邻或空行段落间距同步 |
| 定理与证明边界 | `\begin{theorem}[简称]\label{thm:1}` / `\begin{theoremn}{1-a}[简称]\label{...}` / `\begin{proof}` | `::: 定理 {#thm:1} 简称` / `::: 定理 {#... num=1-a} 简称` / `::: 证明` ... `:::` | 环境边界只读（增删改触发 `[需人工处理]`）；内部段落正常最小差异回写 |
| 无序列表 | `\begin{itemize}` + `\item ...`（支持项内嵌套 `equation`） | `- ...` | `patch_list_minimal` 逐项最小替换，保留未改项尾注 |
| 管道三线表 | `\begin{htdtable}{colspec}\toprule...\midrule...\bottomrule\end{htdtable}` | 标准 Markdown 管道表 `\| A \| B \|` | 双向互转 |
| 编号浮动表 | `\begin{table}[htbp]...\caption{...}\label{tab:1}...\end{table}` | `<figure class="tbl" data-label="tab:1">...</figure>` | 只读浮动体：未改时原样保留局部排版微调，篡改触发 `[需人工处理]` |
| Standalone 图/算法 | `\htdfig{figs/fig1.tex}{fig:1}{图题}` | `![图题](figs/fig1.tex){#fig:1}` | 只读浮动图：未改原样保留，篡改触发 `[需人工处理]` |
| 原生图片浮动体 | `\begin{figure}...\includegraphics{...}\caption{...}\label{fig:x}\end{figure}` | `<figure class="fig" data-label="fig:x"><img src="figs/....svg" alt=""><figcaption>...</figcaption></figure>` | 只读浮动体：未改原样保留，篡改触发 `[需人工处理]` |
| 原生算法浮动体 | `\begin{algorithm}...\caption{...}\label{alg:x}...\end{algorithm}` | `<figure class="alg" data-label="alg:x" data-tex="algs/x.tex"><figcaption>...</figcaption><!--TEX--></figure>`（导入期自动拆分 `src/algs/x.tex`） | 只读浮动体：未改原样保留原块或 `\input`，篡改触发 `[需人工处理]` |
| 文献与透传注释 | `\bibliography{html/src/refs}` / `% <!-- p.11 -->` | `<!--REFS-->` / `<!-- p.11 -->` | 双向一一对应 |
| 文末脚注定义 | `\htdfntext{1}{脚注正文}` | `[^1]: 脚注正文` | 双向确定性互转 |

### 行内元素（`tex_inline_to_md` / `md_inline_to_tex`）

| 语义 | TeX 侧写法 | Markdown 侧写法 | 最小差异保留特性 |
| --- | --- | --- | --- |
| 带前缀交叉引用 | `式~\eqref{eq:1}`、`定理~\ref{thm:1}`、`第~\ref{sec:1}~节` | `{@eq:1}`、`{@thm:1}`、`{@sec:1}` | 前字为“公式/方程”等词时不误吞，转为 `公式 ({@eq:1\|n})` |
| 纯编号与自定义锚点 | `\eqref{eq:1}` / `\ref{k}` / `\hyperref[k]{文本}` | `({@eq:1\|n})` / `{@k\|n}` / `{@k\|文本}` | 未改句保留原 `~` 或空格写法 |
| 文献与脚注角标 | `\cite{r01,r02}` / `\htdfnmark{1}` | `[@r01,r02]` / `[^1]` | 双向无损 |
| 强调、代码与链接 | `\textbf{粗}` / `\emph{斜}` / `\texttt{code}` / `\url{https://...}` | `**粗**` / `*斜*` / `` `code` `` / `<a href="https://...">https://...</a>` | 代码与 `$...$` 行内公式内部特殊字符先入栈保护 |
| 间距与转义符 | `~`、`\enspace`、`\_`、`\&`、`\%`、`\#`、`\~{}` | 空格、`_`、`&`、`%`、`#`、`~` | 未改句子原样保留 `~`、`\enspace` 与行尾 `%` 注释 |

## 嵌套 `\input` 零漂移协议

针对大型 `book` / 学位论文在章节 `.tex` 内进一步 `\input{sub}` 的多层目录结构，`manifest.py` 按子文件性质分两类处理：

- 纯浮动体子文件：若 `sub.tex` 整体仅含单个 `algorithm`、`figure` 或 `table` 浮动体，导入期将其展开为对应 `<figure class="alg|fig|tbl" ...>` 供网页渲染与双栏预览，并在父级虚拟视图登记 `input_float_map`；回写期只要该 `<figure>` 未被改动，父 `.tex` 原位保留 `\input{sub}` 一字不改。
- 正文片段子文件：若 `sub.tex` 含章节标题、段落或公式，导入期在生成的章节 `.md` 中包裹成对 HTML 定界注释：

```markdown
<!--tex-file: sections/completed_work/algorithms/error_analysis.tex-->

## 误差界分析 {#cw:sec:err}

此处为子文件转换后的受控 Markdown 正文。

<!--/tex-file-->
```

  - 网页零痕迹：`htd/build.py` 编译 HTML 时原生剥除 HTML 注释，读者端不产生任何多余节点，且双栏 `Ctrl+Click` 行号锚点精确指向该 `.md` 文件内对应行。
  - 分治回写：`export-tex` 扫描每对 `<!--tex-file: REL-->...<!--/tex-file-->`，先将块内正文与 `<tex_root>/REL` 独立执行 `patch_tex` 获得子文件最小差异补丁，再将该块在父级内存中折叠为 `<!--tex-input: REL_NO_EXT-->` 与父 `.tex` 中的 `\input{REL_NO_EXT}` 对齐修补。若任何 `<!--tex-file: ...-->` 缺失、未闭合、嵌套错位或顺序改变，立即触发 `[需人工处理]` 并拒绝写入所有文件。

## 五步最小差异算法与门禁规则

1. 词法保护与单元切分：剥离纯注释行至下一单元 `leading_comments`，记录单元间单换行 `\n` 或空行 `\n\n` 至 `trailing_sep`，将 TeX 与 Markdown 分别解析为 `Unit` 序列。
2. 块级序列对齐：对 `(u.kind, u.md_text, u.meta)` 运行 `SequenceMatcher(autojunk=False)`；`equal` 块直接复用原 `ou.leading_comments + ou.tex_text` 并同步最新块间距 `nu.trailing_sep`。
3. 句级与列表项级最小替换：落入 `replace` 区间的普通段落按中英文句末标点（跳过 `$...$`、`` `...` ``、花括号与方括号内部）切分为句子序列，仅对实际改动的句子调用 `md_inline_to_tex`，其余未改句子原样保留原 TeX 源码（含手工换行、`~`、`\enspace` 与句尾 `%` 注释）；无序列表同理通过 `patch_list_minimal` 仅重编变更项。
4. 只读结构门禁检查：凡删除、新增或修改 `html_table`、`figure`、`algorithm`、`env_open`、`env_close`、`tex_input` 单元，或改动 `main.md` 切片外框架，均收集至 `manual_items` 并向 `stderr` 输出 `[需人工处理] 文件:L行号 原因`。
5. 内存回代强校验与原子提交：对每个补丁结果计算 $F(T')$ 并与目标 Markdown 逐单元比对；仅当**全部**父文件与子文件同时满足 `manual_items == []` 且 $F(T') == M'$ 时，`--apply` 才通过同目录临时文件 + `os.replace` 原子更新实际发生变化的 `.tex` 文件，未变化文件保持原 `mtime` 不动，任一校验不通过则整批 **0 字节写入**。

## 通用 `ctexart` 父级模板（`references/templates/tex-article/`）

`export-tex --init-tex` 使用 `references/templates/tex-article/` 生成独立可编译的中文学术论文骨架：

- `preamble.tex`：通过 `\IfFileExists{html/src/kalman-style.tex}{\input{html/src/kalman-style}}{\usetikzlibrary{...}}` 自动兼容带自定义 TikZ 样式表的工程与普通工程；通过 `\IfFileExists{html/src/alg2e.tex}` / `algcommon.tex` 按需挂载算法宏包；在引入 `html/src/macros.tex` 时局部将 `\newcommand` 重映射为 `\providecommand`，消除 `\bm` 等宏与 `bm` 宏包的重复定义冲突；内置 `\htdfig` 自动区分 `algs/`（`minipage` 排版）与 `figs/`（`lrbox` 超宽自适应缩放）。
- `main.tex` 与 `build.sh`：自动填入标题、副标题、可选 `abstract` 与 `sections/*.tex` 章节列表；若存在 `src/refs.bib` 则自动提取全部条目键写入 `\nocite{...}` 并在 `build.sh` 中串联 `xelatex -> bibtex -> xelatex x2`，若无 `refs.bib` 则自动省略文献钩子并跳过 `bibtex`。
