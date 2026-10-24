# 任务目录规范

## 命名与位置

- 路径: `.agents/.tmp/task/YYYY-MM/YYYY-MM-DD_任务名/` (已 gitignore), 日期按 Asia/Shanghai, 按月划分一级目录, 取任务创建日.
- **跨日续用**: 任务跨日继续时沿用原目录, 不新建; 新一天的工作以新 log 区分 (日期见其文件名). `new_task.py` 对不带日期前缀的任务名优先匹配已有 `????-??-??_任务名`.
- 临时脚本, 实验数据, 中间产物均置于此, 不在 git 跟踪范围内新建.

```text
.agents/.tmp/task/YYYY-MM/YYYY-MM-DD_任务名/
├── docs/
│   ├── plans/     # 计划, 可多份: YYYY-MM-DD_HH-mm_<标题>.md
│   ├── logs/      # 日志, 一个用户 prompt 一份: YYYY-MM-DD_HH-mm_<slug>.md (.current 指向活动 log)
│   └── reports/   # 报告, 按需, 可多份: YYYY-MM-DD_HH-mm_<标题>.md
├── tasks/<slug>/  # 子任务 (按需), 见下文
├── scripts/ data/ # 脚本与输入 (按需)
└── outputs/       # 产出物, 按类型分子目录, 见下文
```

- 三类文档一律放在对应子目录中, `docs/` 根下不放文档文件.
- 文件名时间戳取创建时刻 (`TZ=Asia/Shanghai date '+%Y-%m-%d_%H-%M'`); 标题简短, 可用中文, 不含空格与路径符号.
- 旧版布局用 `new_task.py --migrate` 迁移 (按日 log 改名为 `<日期>_00-00_legacy.md`, 内容不变).

## docs/logs/: 一个用户 prompt 一份

- 每个新的实质性用户 prompt (新需求, 修复, 阶段切换) 用 `--log-new "<slug>" -p "<prompt>"` 新建一份; 脚本会在上一份末尾记 "转入 …" 并更新 `.current`.
- `--log "<事件>"` 向活动 log 的时间线追加一行. 该 log 是此 prompt 的验收索引.
- 字段: 关联日志, 用户原始 prompt (逐字), LLM 理解 (用户明说 / 推断 / 不做), 时间线, 门禁核验 (方法 / 是否执行 / 结果 / 证据), 改动文件 (任务目录内 / 仓库内).

## docs/plans/

- 首份计划由脚本自动建为 `<时间戳>_初始计划.md`.
- 计划发生实质变更 (目标, 方案, 验收标准改变) 时, 用 `--plan "<标题>"` 新建一份, 并在开头注明所修订的上一份; 小幅状态更新直接改当前计划.
- 字段: 署名块, 用户原始 prompt, LLM 理解 (目标, 约束, 产出物), 起止时间, 执行步骤 (勾选列表, 放弃项用 ~~删除线~~), 验收门禁, 验收结果, 用户如何检测.

## docs/reports/

- 主任务级报告 (`docs/reports/`): 主代理向人类汇报的唯一总结入口, 以 `--report "<标题>"` 创建; 凡涉及子代理协作, 数据处理/转换或阶段性交付, 主代理必须在此生成总结报告 (写明主代理做了什么, 各子代理做了什么, 采纳与修复结果, 并链接到各子代理自己的 `docs/reports/`).
- 若需进入 `.tmp` 问答索引, 由 qa-archive 归档摘要并链接回本报告.
- 引用任务目录内其他文件时用 `../../` 起头的相对路径.

## tasks/<slug>/: 子任务 (子代理)

- 开启任何子代理 (含审阅, 调研, 实现) 前, 主代理必须用 `--subtask "<slug>" --agent <名称1> [<名称2> ...]` 创建:
  - `brief.md` (目标, 可写路径, 禁改路径, 交付物, 验收标准)
  - `logs/` (子任务日志, 关联父日志)
  - `agents/<名称>/docs/reports/` 与 `agents/<名称>/docs/logs/` (子代理自包含文档区)
- 权限与落盘:
  - 统一派发具写文件权限的 `self` 子代理 (勿使用无写权限的只读子代理), 严格限制每个子代理只写自己的 `tasks/<slug>/agents/<名称>/`;
  - 每个子代理完成工作后, 必须将自己的详细报告写入 `tasks/<slug>/agents/<名称>/docs/reports/YYYY-MM-DD_HH-mm_<标题>.md` (开头同样含 `get_model_name.py --header` 署名块).
- 向上汇总:
  - 子代理写各自 `agents/<名称>/docs/reports/` → 主代理审阅合并并在主任务 `docs/reports/` 撰写总结报告 → 人类审阅主代理的总结报告 (按需下钻子代理报告).

## outputs/: 结构化存放产出物

- 根下不放散落文件, 按**本任务实际产出的类型**建子目录; 脚本中以常量集中定义各子目录, 不在各处手写路径.
- 示例 (仅供参考, 依任务取舍, 勿照搬): 一个训练类任务可分为

```text
outputs/
├── figures/      # 图像
├── metrics/      # 曲线与指标 (json, csv)
├── checkpoints/  # 模型权重
└── logs/         # 运行日志
```

## 通用约定

- 排版: 数据陈列 (指标, 对比, 统计) 用表格; 其余 (字段说明, 步骤, 门禁, 日志) 一律用列表.
- 所有文档开头均放置署名块 (`get_model_name.py --header` 输出): agent name, harness, session (前 8 位 + conversation:// 链接), time.
- 目录更名或文件移动时同步修正仓库内对旧路径的引用.
