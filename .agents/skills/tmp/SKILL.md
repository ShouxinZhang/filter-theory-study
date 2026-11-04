---
name: tmp
description: '.tmp 工作区总入口, 路由到三个子技能: qa-archive (用户输入 .tmp 时的问答归档, README 索引, < n 行校验), task (.agents/.tmp/task/YYYY-MM/ 下按月归档任务目录, docs/plans, logs, reports 三个子目录存档) 与 session-map (Antigravity / Codex App 本地长会话订阅查询与管理、讨论树 map.md 与渐进折叠记录 prompts.md 热同步).'
---

# tmp

按场景选择子技能, 先读对应 `SKILL.md`, 细则再按需查阅其 `references/`.

| 场景 | 子技能 | 入口 |
| --- | --- | --- |
| 用户输入 `.tmp`, 需将回答归档为周目录 Markdown; 用户要求 `< n` 行 | qa-archive | [qa-archive/SKILL.md](qa-archive/SKILL.md) |
| 需要临时脚本, 实验数据或多步执行的任务 | task | [task/SKILL.md](task/SKILL.md) |
| Antigravity / Codex App 会话订阅查询、详情、订阅/退订，讨论树与折叠记录热同步 | session-map | [session-map/SKILL.md](session-map/SKILL.md) |

可组合触发: 任务的重型报告位于 task 目录的 `docs/reports/`, 若需进入 `.tmp` 问答索引, 由 qa-archive 归档摘要并链接回报告.

## 目录

```text
tmp/
├── SKILL.md                 # 本路由
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
    ├── references/          # codex.md, subscriptions.md
    ├── scripts/             # sync.py, codex.py
    └── tests/               # 解析与热同步回归测试
```
