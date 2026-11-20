---
name: html-tex-doc-charts
description: 为 html-tex-doc 与学术论文生成主题自适应内联 SVG 与单页矢量 PDF 数据图，内置 mathjax-full 矢量公式渲染与防越界门禁，严格分离 CSS 主题包、HTML 打印壳模板、SVG 图标素材与纯 Python 渲染引擎。
---

# html-tex-doc / charts

面向无分页 HTML 论文与 XeLaTeX PDF 的解耦数据绘图子技能。所有样式、打印模板与矢量标记外置；图内数学一律显式写 `$...$` 并由 `mathjax-full` 预渲染为自包含矢量路径，确保与正文 MathJax 100% 同源。

## 速查

```bash
C=.agents/skills/chores/html-tex-doc/charts/scripts/charts_cli.py

# 查看已安装主题包
python3 $C themes

# 基于模板创建新主题包（默认落盘到 assets/themes/<name>/）
python3 $C init-theme <theme-name>

# 为新论文生成仿真与出图脚手架（simulate.py + build_charts.py）
python3 $C init-paper <target-dir>

# 将目录或指定 SVG 批量导出为无边距单页矢量 PDF
python3 $C export-pdf <svg-dir-or-files...> [--theme editorial-academic]
```

## 硬性规范与对接契约

- 图内数学：标题、副标题、图例、坐标轴与标注中的数学公式必须用 `$...$` 显式包裹（默认 `strict_math=True`，禁止裸 `κ`/`σ`/`x_k`），构建期由 `scripts/mathjax_svg.mjs` 转为矢量路径嵌入。
- 布局门禁：标注自动钳位在绘图区内严禁撞击标题与图例；交付前必须无头 Chrome 截图目视复核暗/浅色实图。
- 文档对接：产出带 `data-htd-inline="1"` 的 SVG 与同名矢量 PDF 至论文 `html/src/figs/`，自动跟随宿主深浅色主题与 XeLaTeX 印刷链路。

## 架构分层

- `assets/`：运行时正式静态资产（`base.css`、`themes/<name>/`、`glyphs/*.svg`）。
- `references/templates/`：可复用脚手架（`pdf-print/pdf_print.html`、`chart-theme/`、`paper-charts/`）。
- `references/examples/`：风格参考卡与真实论文范例（`anthropic-editorial/`、`gordon1993/`、`julier1997/`）。
- `scripts/`：纯 Python 几何引擎（`htd_charts/`）与 `mathjax_svg.mjs`，禁止硬编码 HTML/CSS/SVG path。

## 参考

- [references/spec.md](references/spec.md): 主题包结构、图内 MathJax 规范、防越界门禁与视觉复核细则。
- [references/examples/gordon1993/README.md](references/examples/gordon1993/README.md): Gordon (1993) 11 张中英双语科研数据图范例。
- [references/examples/julier1997/README.md](references/examples/julier1997/README.md): Julier & Uhlmann (1997) 6 张中文科研数据图范例。
- [references/examples/anthropic-editorial/README.md](references/examples/anthropic-editorial/README.md): 编排型数据图视觉风格参考卡。
