# 行数校验规则

用户在末尾输入 `< 20`, `< 10` 等, 表示文档折算行数须严格小于 $n$.

## 折算方式

- 普通非空行各计 1 行.
- 公式块 (含首尾 `$$` 行) 不超过 10 行时整体计 1 行; 超过阈值则按物理行计.
- 阈值可由 `--math-max` 调整, 默认 10.

## 命令

```bash
python3 .agents/skills/tmp/qa-archive/scripts/count_lines.py -m <n> <文件>
python3 .agents/skills/tmp/qa-archive/scripts/count_lines.py -m <n> --math-max 10 <文件>
```

`archive_tmp.py -m <n>` 在归档前调用同一函数, 超出即报错中断, 不写入索引.
