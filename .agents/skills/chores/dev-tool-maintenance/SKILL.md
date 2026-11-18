---
name: dev-tool-maintenance
description: 本机开发工具维护。按故障或操作路由 Antigravity/agy 升级、VS Code LaTeX Workshop 构建修复，以及 Codex 的 Claude 对话导入、停用同步和侧栏残留清理。
---

# 开发工具维护

| 用户场景 | 子技能 | 入口 |
| --- | --- | --- |
| 检查或升级 Antigravity 桌面端，配置 agy 安装助手或回滚版本 | agy-update | [agy-update/SKILL.md](agy-update/SKILL.md) |
| VS Code 报 Recipe terminated with error，或编辑器所用引擎、根文件、输出目录与预期不符 | latex-workshop-build-fix | [latex-workshop-build-fix/SKILL.md](latex-workshop-build-fix/SKILL.md) |
| Codex 侧栏出现 Claude 对话，希望停止同步、整理或删除导入副本，或删除后侧栏仍显示 | codex-imported-chats | [codex-imported-chats/SKILL.md](codex-imported-chats/SKILL.md) |

```text
dev-tool-maintenance/
├── SKILL.md
├── agy-update/
├── latex-workshop-build-fix/
└── codex-imported-chats/
```
