---
name: qa-archive
description: 用户输入 .tmp 时, 将回答按周归档到 .agents/.tmp/agent/, 校验 < n 行 (公式块 <=10 行计 1 行), 并同步 README 周期表与索引.
---

# qa-archive

## 速查

```bash
# 归档并更新 README 索引 (可选行数校验)
python3 .agents/skills/tmp/qa-archive/scripts/archive_tmp.py -f <文档> [-t 类型] [-m N]
# 单独统计折算行数
python3 .agents/skills/tmp/qa-archive/scripts/count_lines.py -m N <文档>
# 仅刷新 README 周期表
python3 .agents/skills/tmp/qa-archive/scripts/archive_tmp.py --refresh-only
```

## 流程

1. 以 `TZ=Asia/Shanghai date '+%Y-%m-%d_%H-%M'` 生成文件名, 放入所属周目录.
2. 开头声明 `agent name: <model slug>` (见 `get-model-name` 技能).
3. 用户要求 `< n` 行时, 以 `-m n` 校验.
4. 运行 `archive_tmp.py` 追加索引并刷新周期表.

## 参考

- [references/qa-archive.md](references/qa-archive.md): 周目录划分, 文件命名, README 索引, 旧文档迁移.
- [references/line-count.md](references/line-count.md): `< n` 行折算规则与脚本参数.
