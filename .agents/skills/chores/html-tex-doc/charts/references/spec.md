# html-tex-doc/charts 架构与主题规范

## 1. 四层解耦原则

- 静态资产层（`assets/`）：存放运行时直接加载的 `base.css`，主题包 `themes/<name>/{tokens.css,theme.json}` 与外置矢量图标 `glyphs/*.svg`。
- 模板层（`references/templates/`）：存放已提炼的可复用脚手架，包括无头 Chrome 矢量 PDF 打印壳 `pdf-print/pdf_print.html`，新建主题包骨架 `chart-theme/` 与新论文出图骨架 `paper-charts/`。
- 范例层（`references/examples/`）：存放具体风格素材参考与真实论文的完整仿真与出图范例；新收集的视觉风格可先在此沉淀，成熟后再提炼为 `assets/themes/` 正式主题。
- 引擎层（`scripts/htd_charts/` + `scripts/mathjax_svg.mjs`）：纯几何计算，MathJax 矢量公式预渲染与 SVG 装配，严禁在 `.py` 文件中硬编码 CSS 规则，HTML 打印壳或矢量图标路径坐标。

## 2. 语义角色与主题层叠

Python API 只引用语义角色名（`primary`，`secondary`，`accent`，`aux`，`fg`，`card`，`muted`），具体配色与字体全部由 CSS 变量控制，按三层层叠加载：

- 基础层：`assets/base.css`
- 主题层：`assets/themes/<name>/tokens.css`（及可选 `chart.css`）
- 论文覆盖层：`Chart(..., override_css=Path(".../theme.css"))`

## 3. 图内 MathJax 矢量排版硬规则

- 严禁靠正则表达式猜字符或用普通 Unicode 字符（如裸 `κ`，`σ`，`x₅`，`×10⁻³`）替代数学公式。
- 图表标题，副标题，图例，坐标轴标题与数据标注中的所有数学变量与公式，一律显式使用 `$...$` 定界符（例如 `缩放参数 $\kappa$`，`$n + \kappa = 3$`，`$\times 10^{-3}$`，`$\dot{x}_k$`）。
- `Chart.render()` 在构建期通过 `scripts/mathjax_svg.mjs` 调用仓库 `mathjax-full`（`SVG` 输出器，`fontCache: "none"`）将全部 `$...$` 批量转为自包含矢量 `<path>` 并按基线精确对齐嵌入图表；默认开启 `strict_math=True`，检测到裸数学符号时直接报错拒出。
- 矢量路径统一使用 `fill="currentColor"`，自动继承浅色与深色模式 CSS 变量，并在 XeLaTeX PDF 导出中保持与正文 MathJax 100% 一致的字形。

## 4. 标注防越界与交付前视觉复核门禁

- 坐标轴范围必须完整容纳关键数据峰值并预留标注空间；`add_callout()` 默认将标注锚点与引线钳位在绘图区 `[y_top + 16, y_bot - 6]` 内部，严禁任何标注越界压盖标题，副标题或图例。
- 凡新增或重绘论文数据图，交付前必须执行三项门禁校验：
  - 单元测试与 `skill_ctl.py lint` 全部通过；
  - 用无头 Chrome 截取代表性图表（含深色与浅色模式）并目视复核，确认图内公式均为真 MathJax 矢量字形且文字零重叠；
  - 若同步更新论文站点，须校验 `index.html` 中参考文献条目（`<!--REFS-->`）与脚注（`<!--FOOTNOTES-->`）非空且 `import-tex --check` 为 0 差异。
