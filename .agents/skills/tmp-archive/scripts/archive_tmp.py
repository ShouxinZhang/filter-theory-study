#!/usr/bin/env python3
"""
tmp-archive: 自动更新 .agents/.tmp/agent/README.md 归档索引与周文档计数
"""

import argparse
import re
import sys
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parents[3]
TMP_AGENT_DIR = AGENTS_DIR / ".tmp" / "agent"
README_PATH = TMP_AGENT_DIR / "README.md"
WEEK_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}$")


def extract_title(file_path: Path) -> str:
    """提取 Markdown 文档的一级标题，缺省使用文件名"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
    except Exception:
        pass
    return file_path.stem


def refresh_week_table(content: str) -> str:
    """统计各周目录实际 .md 文档数，更新 README 顶部的周期表格"""
    if not TMP_AGENT_DIR.exists():
        return content

    week_counts = {}
    for entry in TMP_AGENT_DIR.iterdir():
        if entry.is_dir() and WEEK_DIR_PATTERN.match(entry.name):
            md_count = len(list(entry.glob("*.md")))
            week_counts[entry.name] = md_count

    sorted_weeks = sorted(week_counts.keys(), reverse=True)
    table_lines = ["| 周期 | 文档数 |", "| --- | --- |"]
    for week in sorted_weeks:
        table_lines.append(f"| [{week}]({week}/) | {week_counts[week]} |")
    new_table_str = "\n".join(table_lines)

    table_pattern = re.compile(
        r"\| 周期 \| 文档数 \|\n\| -+ \| -+ \|\n(?:\| \[.*?\]\(.*?\) \| \d+ \|\n*)+",
        re.MULTILINE,
    )
    if table_pattern.search(content):
        return table_pattern.sub(new_table_str, content, count=1)
    return content


def check_max_lines(file_path: Path, max_lines: int) -> bool:
    """检查文件行数是否严格满足 < max_lines"""
    with open(file_path, "r", encoding="utf-8") as f:
        line_count = sum(1 for _ in f)
    print(f"[wc -l] {file_path.name}: {line_count} 行 (目标: < {max_lines})")
    if line_count >= max_lines:
        print(f"Error: 行数 {line_count} 超出限制 (< {max_lines})！", file=sys.stderr)
        return False
    return True


def register_document(file_path: Path, doc_type: str, max_lines: int | None = None) -> None:
    if not file_path.exists():
        print(f"Error: 文件不存在: {file_path}", file=sys.stderr)
        sys.exit(1)

    if max_lines is not None:
        if not check_max_lines(file_path, max_lines):
            sys.exit(1)

    if not README_PATH.exists():
        print(f"Error: README 不存在: {README_PATH}", file=sys.stderr)
        sys.exit(1)

    content = README_PATH.read_text(encoding="utf-8")

    # 计算相对周目录路径
    try:
        rel_to_agent = file_path.relative_to(TMP_AGENT_DIR)
    except ValueError:
        print(f"Error: 文件不在 {TMP_AGENT_DIR} 下: {file_path}", file=sys.stderr)
        sys.exit(1)

    title = extract_title(file_path)
    entry_line = f"新增{doc_type}: [{title}]({rel_to_agent.as_posix()})。"

    # 检查是否已有该文件的链接
    if rel_to_agent.as_posix() not in content:
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n{entry_line}\n"
        print(f"已追加索引: {entry_line}")
    else:
        print(f"文件已在索引中: {rel_to_agent.as_posix()}")

    # 刷新表格
    updated_content = refresh_week_table(content)
    README_PATH.write_text(updated_content, encoding="utf-8")
    print("README 周期表格与索引更新完毕。")


def main():
    parser = argparse.ArgumentParser(description="更新 .agents/.tmp/agent/README.md 归档索引")
    parser.add_argument("--file", "-f", type=Path, help="待归档或新增的 markdown 文件路径")
    parser.add_argument("--type", "-t", default="讨论", help="新增条目类型(如: 讨论, 推导, 报告, 习题)")
    parser.add_argument("--max-lines", "-m", type=int, default=None, help="最大行数限制(检查严格小于该值)")
    parser.add_argument("--refresh-only", action="store_true", help="仅重新统计并刷新周表格")

    args = parser.parse_args()

    if args.refresh_only or not args.file:
        if not README_PATH.exists():
            print(f"Error: {README_PATH} 不存在", file=sys.stderr)
            sys.exit(1)
        content = README_PATH.read_text(encoding="utf-8")
        updated = refresh_week_table(content)
        README_PATH.write_text(updated, encoding="utf-8")
        print("周期表格刷新完毕。")
        return

    register_document(args.file.resolve(), args.type, args.max_lines)


if __name__ == "__main__":
    main()
