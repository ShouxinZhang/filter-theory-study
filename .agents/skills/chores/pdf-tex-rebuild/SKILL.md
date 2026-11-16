---
name: pdf-tex-rebuild
description: "PDF 逆向重建 TeX 技能。Use when: 需要从论文 PDF 逆向回溯 LaTeX 结构、抽取公式/图/表/算法锚点、恢复引用关系、自动裁图、生成 BibTeX、并导出带短标题与说明的可编辑重建稿。"
---
# PDF TeX Rebuild

## 用途

用于从论文 PDF 逆向回溯一个“可继续编辑”的 TeX 重建稿与配套中间产物，而不是声称自动恢复原始源码。

## 强制分流

1. 先查官方 TeX 源码；存在源码时直接以源码为权威，不对已有正文和公式做 OCR。
2. 只有 PDF 时，默认渲染页面并由模型直接视觉 OCR；必须完整阅读 `./references/ocr-first-workflow.md`。
3. `pdftotext` 仅用于覆盖率提示；Python 抽取脚本只作为可选清单工具，不得默认生成最终正文、公式、表格和阅读顺序。
4. 写正文前必须选择 TeX 模板；必须完整阅读 `./references/template-contract.md`。没有用户模板时使用内置单栏模板，禁止自行引入双栏。

核心目标：

- 逐页直接视觉 OCR，并用页面台账控制覆盖率和人工复核。
- 识别公式、图、表、算法等带编号对象，给出稳定 `label`。
- 扫描正文中的 `Equation/Figure/Table/Algorithm` 引用，并尽量绑定到对应锚点。
- 基于明确模板生成可继续翻译、补图、修公式的 LaTeX 稿。
- 自动裁剪原 PDF 中的 figure 区域并回填为图片资产。
- 从参考文献列表生成 `.bib` 初稿，并切换到 BibTeX 驱动。
- 默认把 figure/algorithm 导出成“短标题 + 说明”的结构，而不是把长段落直接塞进 `\caption{}`。

## 模块结构

- `SKILL.md`：技能入口与适用边界
- `references/`：流程、约束、输出 schema、启发式说明
- `scripts/`：抽取、映射、重建、测试脚本
- `assets/templates/`：可直接复制并编译的单栏中英 TeX 模板

## 使用方式

1. 阅读 `./references/index.md`、`./references/ocr-first-workflow.md` 和 `./references/template-contract.md`。
2. 渲染 PDF，建立逐页台账，直接查看页面并分批转录。
3. 使用 `./scripts/init_tex_template.sh <destination>` 初始化单栏模板；若用户指定模板，则直接复用用户模板。
4. 为每个编号对象立即建立稳定标签，并把正文引用写成 `\eqref`/`\ref`；文献引用必须跳转到条目。
5. 只有在清单统计确实有帮助时，才执行 `./scripts/build.sh <pdf_path> [case_name]`，其输出不得覆盖人工 OCR 正文。
6. 按 `./references/workflow.md` 完成逐页视觉闭环；可选运行裁图、BibTeX 和 smoke-test 脚本。

## 默认约束

- 产出物默认写入 `.agents/.tmp/task/pdf-tex-rebuild/<case_name>/`（或通过 `PDF_TEX_OUT_DIR` 指定当前任务的 `outputs/`）。
- 不复制原 PDF 大文件到输出目录，只记录源文件路径。
- 默认直接 OCR 只依赖 `pdfinfo`、`pdftoppm`/`mutool` 与视觉查看能力；不默认依赖 Python OCR。
- `pdftotext`、`pdftohtml`、`python3` 仅供可选清单脚本使用；脚本输出必须人工核对。
- 若要自动裁图，还依赖 `pdftocairo`、`convert`、`identify`。
- 若要生成 BibTeX 并编译重建稿，依赖 `bibtex` 或兼容工具链。
- 自动引用绑定只保证“高召回 + 显式不确定项”，不承诺 100% 正确。
- 单栏是 PDF-only 默认模板；除非用户明确要求，不得改为双栏。
- 用户指定的 sandbox/template 在栏数、纸张、字号、字体、页边距、段落和标题样式上具有最高优先级。
- 数学粗体统一使用 `\bm`；所有公式、图表和文献引用必须生成实际可点击链接。
- 公式编号与最终排版编号分离：内部主键使用稳定 `label`，必要时在 stub 中临时保留原 PDF 编号。
- figure 与 algorithm 默认使用短 `caption`；详细解释应导出为浮动体内说明，而不是长段落式标题。
