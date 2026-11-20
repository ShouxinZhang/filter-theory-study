---
name: chores
description: '杂务总入口: 本机运维、工具排障、PDF 视觉 OCR 重建 TeX 与无分页混合排版，包含 HTML+TeX 无页混合文档构建与毫秒级双向 TeX 互换（html-tex-doc）、PDF 视觉 OCR 逆向重建 TeX（pdf-tex-rebuild）、须先询问用户的 Blender 实验工作流、开发工具维护（Antigravity/agy 升级、VS Code LaTeX Workshop 构建失败、Codex 自动导入 Claude 对话与侧栏残留），按场景路由到对应子技能。'
---

# chores

按场景选择子技能, 先读对应 `SKILL.md`, 细则再按需查阅其 `references/`.

| 场景 | 子技能 | 入口 |
| --- | --- | --- |
| 无分页 HTML/受控 Markdown + TeX standalone 出图与算法的混合排版工作流，内置 import-tex/export-tex 毫秒级 TeX 双向互换与最小差异回写，支持可折叠目录、Web 双栏编辑器、全文搜索及 Ctrl+Click 双向高亮对齐。 | html-tex-doc | [html-tex-doc/SKILL.md](html-tex-doc/SKILL.md) |
| 从论文 PDF 视觉 OCR 逆向回溯可编辑 TeX 重建稿，抽取公式/图/表/算法锚点、恢复引用关系、自动裁图并生成 BibTeX。 | pdf-tex-rebuild | [pdf-tex-rebuild/SKILL.md](pdf-tex-rebuild/SKILL.md) |
| Blender 实验技能：运维、bpy 开发与果冻案例。由 agent 编写，用户尚无 Blender 经验及审核能力；参考执行前必须先询问用户，谨慎核验。 | blender | [blender/SKILL.md](blender/SKILL.md) |
| Antigravity/agy 升级、LaTeX Workshop 构建失败、Codex 出现 Claude 对话或删除后侧栏仍显示 | dev-tool-maintenance | [dev-tool-maintenance/SKILL.md](dev-tool-maintenance/SKILL.md) |

## 目录

```text
chores/
├── SKILL.md                 # 本路由
├── html-tex-doc/            # 无分页 HTML/Markdown + TeX 混合排版、双向互换与双栏编辑工作流
│   ├── SKILL.md
│   ├── charts/              # 子技能：解耦数据绘图引擎（主题包、外置模板/图标与范例）
│   ├── references/          # spec.md, texsync.md, templates/{src,academic-md,tex-article}, examples/...
│   └── scripts/             # html_tex_doc.py (init/build/serve/import-tex/export-tex), htd/texsync/
├── pdf-tex-rebuild/         # PDF 视觉 OCR 逆向重建可编辑 TeX 工作流
│   ├── SKILL.md
│   ├── references/          # ocr-first-workflow.md, template-contract.md, workflow.md 等
│   ├── scripts/             # build.sh, init_tex_template.sh, extract_figures.sh, smoke_test.sh 等
│   └── assets/templates/    # 单栏中英 TeX 模板 (single-column-bilingual)
├── blender/                 # 实验技能，参考执行前必须先询问用户
│   ├── SKILL.md
│   ├── references/
│   ├── scripts/
│   └── assets/
└── dev-tool-maintenance/    # 本机开发工具维护
    ├── SKILL.md
    ├── agy-update/
    ├── latex-workshop-build-fix/
    └── codex-imported-chats/
```
