# Workflow

## 标准流程

1. 先确认是否有官方 TeX 源码。有则停止 PDF OCR，以源码为权威。

2. PDF-only 时先渲染页面：

```bash
pdfinfo <pdf_path>
mkdir -p <case_dir>/page-renders
pdftoppm -png -r 180 <pdf_path> <case_dir>/page-renders/page
```

3. 建立 `page-ledger.md`，由模型直接查看每页并转录。每页正文、公式、图表、脚注和文献均需单独勾选“已转录/已视觉核对”。

4. 先复制模板，再写论文内容：

```bash
bash .agents/skills/pdf-tex-rebuild/scripts/init_tex_template.sh <destination>
```

若用户指定现有模板或 sandbox，则不运行默认模板脚本，直接复制和复用用户模板。

5. 只有需要自动清点对象时，才运行布局抽取：

```bash
bash .agents/skills/pdf-tex-rebuild/scripts/build.sh <pdf_path> [case_name]
```

该脚本输出是待核对清单，不得覆盖直接 OCR 写成的正文。

6. 查看可选抽取输出：

```bash
find .agents/.cache/skill_output/pdf-tex-rebuild/<case_name> -maxdepth 2 -type f | sort
```

7. 将 `parsed/report.md`、`anchors.json` 和 `refs.json` 与页面台账逐项比对；自动识别不能替代视觉核对。

8. 若要裁图或生成 `.bib` 初稿，可执行：

```bash
bash .agents/skills/pdf-tex-rebuild/scripts/extract_figures.sh \
  .agents/.cache/skill_output/pdf-tex-rebuild/<case_name> <pdf_path> <figure_dir>
bash .agents/skills/pdf-tex-rebuild/scripts/list_to_bib.sh <tex_path> <output_bib>
```

9. 编译 TeX，渲染全部输出页并与原 PDF 逐页比较；之后才运行可选 smoke test：

```bash
bash .agents/skills/pdf-tex-rebuild/scripts/smoke_test.sh <pdf_path>
```

## 推荐使用顺序

- 首次建案例：直接 OCR + 页面台账 + `init_tex_template.sh`
- 自动清点：`build.sh`（可选，不产出最终正文）
- 调试自动引用：修改脚本后重新跑 `build.sh`
- 验收自动脚本：`smoke_test.sh`

## 编号恢复策略

- 公式：用 `\tag{n}` 临时保留原编号，同时保留 `\label{eq:auto-n}`。
- 图表：按编号顺序设置计数器，优先保证 `\ref` 可用。
- 图与算法：默认导出为“短标题 + 说明”两段式，而不是把长说明全部塞进 `\caption{}`。
- 后续人工定稿时，可以移除 `\tag`，让 LaTeX 重新编号，但正文仍应通过 `label/ref` 维持引用稳定。
