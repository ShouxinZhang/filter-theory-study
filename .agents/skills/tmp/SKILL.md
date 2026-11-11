---
name: tmp
description: '.tmp 工作区总入口: qa-archive 负责问答周归档与行数校验; task 负责任务工作区; session-map 负责会话订阅、讨论树与记录热同步、session 专属记忆草稿和人类审核后的正式 memory; communication-science 在用户明确要求时提供交流与语气示范。'
---

# tmp

按场景选择子技能, 先读对应 `SKILL.md`, 细则再按需查阅其 `references/`.

| 场景 | 子技能 | 入口 |
| --- | --- | --- |
| 用户明确要求阅读交流科学、语气示范或使用本技能 | communication-science | [communication-science/SKILL.md](communication-science/SKILL.md) |
| 用户输入 `.tmp`, 需将回答归档为周目录 Markdown; 用户要求 `< n` 行 | qa-archive | [qa-archive/SKILL.md](qa-archive/SKILL.md) |
| 需要临时脚本, 实验数据或多步执行的任务 | task | [task/SKILL.md](task/SKILL.md) |
| 会话订阅、讨论树与记录热同步；session 记忆整理、审核与上下文恢复 | session-map | [session-map/SKILL.md](session-map/SKILL.md) |

可组合触发: 任务的重型报告位于 task 目录的 `docs/reports/`, 若需进入 `.tmp` 问答索引, 由 qa-archive 归档摘要并链接回报告.

## 目录

```text
tmp/
├── SKILL.md                 # 本路由
├── communication-science/
│   ├── SKILL.md
│   ├── references/          # 语气示范.md
│   ├── scripts/             # 预留
│   └── agents/              # 显式调用配置
├── qa-archive/
│   ├── SKILL.md
│   ├── references/          # qa-archive.md, line-count.md
│   └── scripts/             # archive_tmp.py, count_lines.py
├── task/
│   ├── SKILL.md
│   ├── references/          # task-layout.md + templates/
│   └── scripts/             # new_task.py
└── session-map/
    ├── SKILL.md
    ├── references/          # codex.md, subscriptions.md, memory.md, templates/
    └── scripts/             # sync.py, memory.py, tests/ 等
```
