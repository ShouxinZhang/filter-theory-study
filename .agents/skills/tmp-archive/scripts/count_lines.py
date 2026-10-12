#!/usr/bin/env python3
"""行数统计：独立公式块（$$...$$ 或 \\[...\\]）总行数 <= 阈值时整体计 1 行，超过则按实际行数计。

围栏代码块内的 `$$` 不视为公式，按实际行数计。
"""
import argparse
import sys
from pathlib import Path

MATH_MAX = 10  # 公式块（含分隔符行）不超过该行数则折算为 1 行


def count_lines(text: str, math_max: int = MATH_MAX) -> tuple[int, int, int]:
    """返回 (折算行数, 物理行数 wc -l 口径, 折算的公式块数)。"""
    lines = text.splitlines()
    total = 0
    blocks = 0
    in_code = False
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_code = not in_code
            total += 1
            i += 1
            continue
        if not in_code:
            opener = closer = None
            if s.startswith("$$"):
                opener, closer = "$$", "$$"
            elif s.startswith("\\["):
                opener, closer = "\\[", "\\]"
            if opener:
                rest = s[len(opener):]
                if closer in rest:  # 单行公式
                    total += 1
                    blocks += 1
                    i += 1
                    continue
                j = i + 1
                while j < len(lines) and closer not in lines[j]:
                    j += 1
                if j < len(lines):
                    n = j - i + 1
                    if n <= math_max:
                        total += 1
                        blocks += 1
                    else:
                        total += n
                    i = j + 1
                    continue
        total += 1
        i += 1
    return total, len(lines), blocks


def main() -> None:
    p = argparse.ArgumentParser(description="公式块折算行数统计")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--max-lines", "-m", type=int, default=None, help="要求折算行数严格小于该值")
    p.add_argument("--math-max", type=int, default=MATH_MAX, help="公式块折算为 1 行的最大物理行数")
    a = p.parse_args()
    bad = False
    for f in a.files:
        eff, phys, blocks = count_lines(f.read_text(encoding="utf-8"), a.math_max)
        msg = f"{f}: 折算 {eff} 行 (物理 {phys} 行, 公式块折算 {blocks} 个)"
        if a.max_lines is not None:
            ok = eff < a.max_lines
            msg += f" 目标 < {a.max_lines}: {'OK' if ok else 'FAIL'}"
            bad |= not ok
        print(msg)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
