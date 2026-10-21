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
python3 $S -n <任务名> --report "<标题>"               # 新增一份报告
python3 $S -n <任务名> --subtask "<slug>"              # 开启子代理前建子任务区
python3 $S -n <任务名> --migrate                       # 旧版布局迁移
```

## 目录

```text
docs/
├── plans/     YYYY-MM-DD_HH-mm_<标题>.md   (可多份)
├── logs/      YYYY-MM-DD_HH-mm_<slug>.md   (一个用户 prompt 一份)
└── reports/   YYYY-MM-DD_HH-mm_<标题>.md   (按需, 可多份)
tasks/<slug>/  brief.md, logs/, agents/<名称>/ (子代理唯一可写区)
outputs/       按本任务实际产出类型分子目录 (示例见 task-layout.md, 勿照搬)
```

## 流程

- 任务开始: 运行 `new_task.py` 建立目录, 初始计划与首份 log; 填写 LLM 理解, 执行步骤, 验收门禁.
- 每个新的用户 prompt: `--log-new` 新建 log (跨日亦沿用原任务目录); 执行中以 `--log` 追加事件, 步骤状态同步至当前计划.
- 开启子代理: 先 `--subtask` 建 brief 与子日志, 子代理只写自己的 `agents/<名称>/`, 主代理合并并在父 log 记录.
- 完成时: 在 log 中填写门禁核验与改动文件, 在计划中填写验收结果; 重型结论以 `--report` 写入报告.

## 参考

- [references/task-layout.md](references/task-layout.md): 目录命名, 各类文档字段, 子任务与 outputs 约定.
- [references/templates/](references/templates/): `plan.md`, `log.md`, `report.md`, `brief.md` 模板, 由脚本读取.
