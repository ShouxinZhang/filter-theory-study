---
name: tmp-archive
description: 用于 .tmp 问答生成后的自动归档、行数硬校验（公式块 <=10 行计 1 行的折算统计 count_lines.py）与 README.md 周期表格和索引的一键同步更新。
---

# tmp-archive

在用户输入 `.tmp` 且生成 Markdown 回答文件后，使用本技能脚本完成行数校验并自动更新归档索引。

## 运行方式

```bash
python3 .agents/skills/tmp-archive/scripts/archive_tmp.py --file <文档路径> [--type <类型>] [--max-lines <N>]
```

- `--file, -f`: 新建的 Markdown 归档文件路径（相对或绝对）。
- `--type, -t`: 记录类别，默认 `讨论`，可选 `推导`、`报告`、`习题`、`记录` 等。
- `--max-lines, -m`: 可选。对应用户的 `< N` 规则，脚本会自动以 `scripts/count_lines.py`（<=10 行公式块计 1 行）校验折算行数是否严格小于 $N$；若超出则报错中断。
- 单独统计：`python3 .agents/skills/tmp-archive/scripts/count_lines.py -m <N> <文件>`，`--math-max` 可调公式块折算阈值（默认 10，含 `$$` 行）。
- `--refresh-only`: 仅重新扫描周目录并刷新 README 顶部的文档计数表格。

## 执行效果

1. **行数校验**：自动核验行数是否合规（目标 `< max_lines`）。
2. **提取标题**：自动解析文档的一级标题 `# ...`。
3. **追加索引**：以 `新增<类型>: [标题](周目录/文件名.md)。` 追加到 `.agents/.tmp/agent/README.md` 末尾（已存在则不重复添加）。
4. **刷新表格**：自动统计各周实际 `.md` 文件数并刷新 README 顶部周期表。
