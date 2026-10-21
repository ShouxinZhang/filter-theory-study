---
name: tmp
description: '.tmp 工作区总入口, 路由到两个子技能: qa-archive (用户输入 .tmp 时的问答归档, README 索引, < n 行校验) 与 task (.agents/.tmp/task/ 下任务目录, docs/plans, logs, reports 三个子目录存档).'
---

# tmp

按场景选择子技能, 先读对应 `SKILL.md`, 细则再按需查阅其 `references/`.

| 场景 | 子技能 | 入口 |
| --- | --- | --- |
| 用户输入 `.tmp`, 需将回答归档为周目录 Markdown; 用户要求 `< n` 行 | qa-archive | [qa-archive/SKILL.md](qa-archive/SKILL.md) |
| 需要临时脚本, 实验数据或多步执行的任务 | task | [task/SKILL.md](task/SKILL.md) |

两者可同时触发: 任务的重型报告位于 task 目录的 `docs/reports/`, 若需进入 `.tmp` 问答索引, 由 qa-archive 归档摘要并链接回报告.

## 目录

```text
tmp/
├── SKILL.md                 # 本路由
├── qa-archive/
│   ├── SKILL.md
│   ├── references/          # qa-archive.md, line-count.md
│   └── scripts/             # archive_tmp.py, count_lines.py
└── task/
    ├── SKILL.md
    ├── references/          # task-layout.md
    │   └── templates/       # plan.md, log.md, report.md, brief.md
    └── scripts/             # new_task.py
```
