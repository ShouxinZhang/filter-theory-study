---
name: task
description: 在 .agents/.tmp/task/YYYY-MM/YYYY-MM-DD_任务名/ 下建立任务目录 (按月归档, 跨日沿用). 文档分 docs/plans/, docs/logs/ (一个用户 prompt 一份), docs/reports/ 三个子目录; 子代理工作区 tasks/<slug>/; 产出物在 outputs/ 下按类型分目录.
---

# task

## 速查

```bash
S=.agents/skills/tmp/task/scripts/new_task.py
python3 $S -n <任务名> -p "<用户原始 prompt>"          # 新建: 初始计划 + 首份 log
python3 $S -n <任务名> --log-new "<slug>" -p "<prompt>" # 新的用户 prompt: 新建一份 log
python3 $S -n <任务名> --log "<事件>"                  # 追加到活动 log 的时间线
python3 $S -n <任务名> --plan "<标题>"                 # 新增一份计划 (计划实质变更时)
python3 $S -n <任务名> --report "<标题>"               # 在主任务 docs/reports/ 新增一份总结报告
python3 $S -n <任务名> --subtask "<slug>" --agent <a1> <a2> # 开启子代理前建子任务区及各子代理 docs/reports/
python3 $S -n <任务名> --migrate                       # 旧版布局迁移
```

## 目录

```text
docs/
├── plans/     YYYY-MM-DD_HH-mm_<标题>.md   (可多份)
├── logs/      YYYY-MM-DD_HH-mm_<slug>.md   (一个用户 prompt 一份)
└── reports/   YYYY-MM-DD_HH-mm_<标题>.md   (主代理汇总报告, 人类直接审阅入口)
tasks/<slug>/
├── brief.md, logs/
└── agents/<名称>/
    └── docs/reports/YYYY-MM-DD_HH-mm_<标题>.md  (子代理自包含报告区, 子代理唯一可写区)
outputs/       按本任务实际产出类型分子目录 (示例见 task-layout.md, 勿照搬)
```

## 流程

- 任务开始: 运行 `new_task.py` 建立目录, 初始计划与首份 log; 填写 LLM 理解, 执行步骤, 验收门禁.
- 每个新的用户 prompt: `--log-new` 新建 log (跨日亦沿用原任务目录); 执行中以 `--log` 追加事件, 步骤状态同步至当前计划.
- 开启子代理 (含审阅, 调研, 实现):
  - 严禁豁免落盘: 先用 `--subtask "<slug>" --agent <名称>` 建立子任务区及各子代理的 `agents/<名称>/docs/reports/`;
  - 派发具写权限的 `self` 子代理 (勿用无写权限的只读子代理), 约束其只写自己的 `tasks/<slug>/agents/<名称>/`, 并将完整工作结果写入 `tasks/<slug>/agents/<名称>/docs/reports/YYYY-MM-DD_HH-mm_<标题>.md`;
  - 主代理负责读取各子代理的 `docs/reports/`, 合并产物并在主任务 `docs/reports/` 生成汇总报告 (附各子代理报告链接), 供人类审阅.
- 完成时: 在 log 中填写门禁核验与改动文件, 在计划中填写验收结果; 阶段性交付或子代理协作均须以 `--report` 在主任务 `docs/reports/` 写入汇总报告.

## 参考

- [references/task-layout.md](references/task-layout.md): 目录命名, 各类文档字段, 子任务与 outputs 约定.
- [references/templates/](references/templates/): `plan.md`, `log.md`, `report.md`, `brief.md` 模板, 由脚本读取.
