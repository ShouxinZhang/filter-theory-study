# Checklist

## 结构

- [ ] 目录符合 `SKILL.md + references/ + scripts/ + assets/templates/`。
- [ ] `references/` 至少包含 `index/workflow/checklist`，并补充 schema 或启发式文档。
- [ ] `scripts/` 仅包含 `*.sh`。

## 功能

- [ ] 有源码/PDF-only 分流明确，PDF-only 默认直接视觉 OCR。
- [ ] 已生成逐页 page ledger，所有页面均完成“转录 + 视觉核对”。
- [ ] 能从内置模板初始化可编译的中英单栏 TeX 项目。
- [ ] 能从 PDF 生成 `meta/raw/parsed/rebuild` 四类产物。
- [ ] 能识别至少一种公式锚点与一种图表锚点。
- [ ] 能扫描正文中的显式引用并生成 `refs.json`。
- [ ] 能生成 `recovered_stub.tex`。

## 引用稳定性

- [ ] 公式使用稳定 `label`，不把数字当主键。
- [ ] stub 中存在保留原编号的策略，例如 `\tag{}` 或计数器回填。
- [ ] 未解析引用会显式暴露在 `report.md` 中。
- [ ] 数学粗体统一为 `\bm`，源码无 `\mathbf`。
- [ ] 公式引用使用 `\eqref`，图表使用 `\ref`，文献引用链接到条目。

## 模板与视觉验收

- [ ] 未经明确要求没有使用双栏。
- [ ] 已核对 class、纸张、字号、字体、页边距、段落和标题样式。
- [ ] 用户指定模板时，已与模板前两页并排核对。
- [ ] 已查看全部输出页，无裁切、重叠、异常空白、乱码或字体漂移。

## 闭环测试

- [ ] 至少运行一次 `smoke_test.sh`。
- [ ] 输出目录位于 `.agents/.cache/skill_output/pdf-tex-rebuild/`。
- [ ] 测试案例能产出非空 `anchors.json`、`refs.json`、`recovered_stub.tex`。
