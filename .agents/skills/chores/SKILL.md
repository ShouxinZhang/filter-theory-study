---
name: chores
description: '杂务总入口: 本机运维、工具排障与无分页混合排版，包含 HTML+TeX 无页混合文档构建（html-tex-doc）、须先询问用户的 Blender 实验工作流、Antigravity/agy 升级及 VS Code LaTeX Workshop 构建修复，按场景路由到对应子技能。'
---

# chores

按场景选择子技能, 先读对应 `SKILL.md`, 细则再按需查阅其 `references/`.

| 场景 | 子技能 | 入口 |
| --- | --- | --- |
| 无分页 HTML/受控 Markdown + TeX standalone 出图与算法的混合排版工作流，支持可折叠目录、Web 双栏编辑器、全文搜索及 Ctrl+Click 双向高亮对齐。 | html-tex-doc | [html-tex-doc/SKILL.md](html-tex-doc/SKILL.md) |
| Blender 实验技能：运维、bpy 开发与果冻案例。由 agent 编写，用户尚无 Blender 经验及审核能力；参考执行前必须先询问用户，谨慎核验。 | blender | [blender/SKILL.md](blender/SKILL.md) |
| 定位并修复 VS Code LaTeX Workshop 构建失败、编译引擎与输出路径问题 | latex-workshop-build-fix | [latex-workshop-build-fix/SKILL.md](latex-workshop-build-fix/SKILL.md) |
| 免密静默升级 Antigravity (agy) 桌面应用: 查询最新版本, 经 sudoers 白名单的 root 脚本下载校验安装到 /opt, 保留上一版本. | agy-update | [agy-update/SKILL.md](agy-update/SKILL.md) |

## 目录

```text
chores/
├── SKILL.md                 # 本路由
├── html-tex-doc/            # 无分页 HTML/Markdown + TeX 混合排版与双栏编辑工作流
│   ├── SKILL.md
│   ├── references/          # spec.md, templates/{src,academic-md}, examples/{linked-list,hithesis-adapter}
│   └── scripts/             # html_tex_doc.py (init/build/serve), md_conv.py, dev_server.py
├── blender/                 # 实验技能，参考执行前必须先询问用户
│   ├── SKILL.md
│   ├── references/
│   ├── scripts/
│   └── assets/
├── agy-update/
│   ├── SKILL.md
│   ├── references/          # README.md: 布局, 安全模型, 回滚
│   └── scripts/             # agy_update.py (用户侧), agy-install.sh (root 助手源)
└── latex-workshop-build-fix/
    └── SKILL.md             # LaTeX Workshop 构建排障
```
