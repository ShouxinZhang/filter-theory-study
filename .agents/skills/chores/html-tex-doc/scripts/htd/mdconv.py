"""受控学术 Markdown → 带源码锚点的 HTML（块级状态机与 main.md 工作区编译）。"""
from __future__ import annotations

import html
import re
from pathlib import Path
from .bib import parse_bib
from .mdinline import MarkdownInline
from .mdsyntax import BOX_OPEN, FENCE_CLOSE, FENCE_OPEN, HEAD, ITEM, MD_FIG, RAW, _inject_attr
from .workspace import INCLUDE_RE, parse_frontmatter, resolve_in_src


class MarkdownCompiler(MarkdownInline):
    def convert(self, text: str, fname: str, start_line: int = 1) -> str:
        ef = html.escape(fname, quote=True)
        off = start_line - 1
        out: list[str] = []
        para: list[tuple[int, str]] = []
        # stack entries: (kind_type, open_line, out_index, base_tag_prefix)
        stack: list[tuple[str, int, int, str]] = []
        prefix = ""
        next_cont = False
        lines = text.split("\n")
        i = 0

        def is_cont_text(raw: str) -> bool:
            s = raw.strip()
            if not s or s == ":::" or s == "---":
                return False
            return not any(p.match(s) for p in (FENCE_OPEN, HEAD, BOX_OPEN, MD_FIG, ITEM, RAW))

        def flush() -> None:
            nonlocal prefix, next_cont
            if para:
                l1, l2 = para[0][0], para[-1][0]
                inner = self.render_lines_with_spans(para, fname, prefix)
                cls = ' class="cont"' if next_cont else ""
                out.append(f'<p{cls} data-file="{ef}" data-l1="{l1}" data-l2="{l2}">{inner}</p>')
                prefix = ""
                next_cont = False
                para.clear()

        while i < len(lines):
            ln = off + i + 1
            line = lines[i].rstrip()
            if m := FENCE_OPEN.match(line):
                tight_top = bool(para)
                flush()
                j = i + 1
                close_lab = None
                while j < len(lines):
                    cm = FENCE_CLOSE.match(lines[j].strip())
                    if cm:
                        close_lab = cm.group(1)
                        break
                    j += 1
                if j == len(lines):
                    self.errors.append(f"{fname}:{ln} 行间公式 $$ 未闭合")
                    end_ln = off + len(lines)
                else:
                    end_ln = off + j + 1
                tight_bot = j + 1 < len(lines) and is_cont_text(lines[j + 1])
                next_cont = tight_bot
                eq_cls = " ".join(c for c, flag in (("tight-top", tight_top), ("tight-bot", tight_bot)) if flag)
                lab = m.group(1) or close_lab
                out.append(self.eq(lab, "\n".join(lines[i + 1 : j]), fname, ln, end_ln, eq_cls))
                i = j + 1
                continue

            if not line.strip():
                flush()
                next_cont = False
            elif line.strip() == ":::":
                flush()
                if not stack:
                    self.errors.append(f"{fname}:{ln} 多余的 :::")
                else:
                    ktype, open_ln, idx, tag_head = stack.pop()
                    out[idx] = f'{tag_head} data-file="{ef}" data-l1="{open_ln}" data-l2="{ln}">'
                    if ktype == "proof":
                        out.append('<p class="qed">∎</p>')
                out.append("</div>")
            elif m := BOX_OPEN.match(line):
                flush()
                kind, label, title = m.group(1), m.group(2), m.group(3).strip()
                idx = len(out)
                if kind in ("证明", "proof"):
                    stack.append(("proof", ln, idx, '<div class="proof"'))
                    out.append('<div class="proof">')
                    prefix = f"<em>{self.inline(title) if title else '证明'}.</em> "
                else:
                    thm_map = {
                        "theorem": "定理",
                        "lemma": "引理",
                        "proposition": "命题",
                        "definition": "定义",
                        "corollary": "推论",
                        "assumption": "假设",
                        "remark": "注",
                    }
                    disp_kind = thm_map.get(kind.lower(), kind)
                    if not label:
                        self.auto += 1
                        label = f"thm:auto-{self.auto}"
                    t = f' data-title="{html.escape(title, quote=True)}"' if title else ""
                    head_prefix = f'<div class="thm" data-kind="{html.escape(disp_kind, quote=True)}" data-label="{html.escape(label, quote=True)}"{t}'
                    stack.append(("thm", ln, idx, head_prefix))
                    out.append(head_prefix + ">")
            elif (m := HEAD.match(line)) and not para:
                lv = len(m.group(1))
                self.sec = self.sec[: lv - 1] + [self.sec[lv - 1] + 1] + [0] * (3 - lv)
                loc = f'data-file="{ef}" data-l="{ln}" data-l1="{ln}" data-l2="{ln}"'
                if lv == 3:
                    num = ".".join(map(str, self.sec))
                    anchor = re.sub(r"[^\w-]", "-", m.group(3) or f"sub-{num}")
                    if m.group(3):
                        self.sub[m.group(3)] = (num, anchor)
                    out.append(f'<h4 id="{anchor}" {loc}><span class="secnum">{num}</span>{self.inline(m.group(2))}</h4>')
                else:
                    lab = f' data-label="{html.escape(m.group(3), quote=True)}"' if m.group(3) else ""
                    out.append(f"<h{lv + 1}{lab} {loc}>{self.inline(m.group(2))}</h{lv + 1}>")
            elif (m := MD_FIG.match(line)) and not para:
                out.append(self._md_figure(m, fname, ln))
            elif not para and (RAW.match(line) or ITEM.match(line)):
                # 若以 <!-- 开头且多行注释，扫描至 -->；普通块扫描至空行
                if line.lstrip().startswith("<!--") and "-->" not in line:
                    j = i + 1
                    while j < len(lines) and "-->" not in lines[j]:
                        j += 1
                    j = min(j + 1, len(lines))
                    out.append("\n".join(lines[i:j]))
                    i = j
                    continue

                j = i
                while j < len(lines) and lines[j].strip():
                    j += 1
                block_pairs = [(off + k + 1, lines[k].rstrip()) for k in range(i, j)]
                l1, l2 = block_pairs[0][0], block_pairs[-1][0]

                if RAW.match(line):
                    rendered_raw: list[str] = []
                    for idx_b, (bln, bline) in enumerate(block_pairs):
                        rline = self.inline(bline)
                        if idx_b == 0:
                            rline = _inject_attr(rline, f'data-file="{ef}" data-l1="{l1}" data-l2="{l2}"')
                        elif re.match(r"^\s*<(tr|figcaption|p|li|h[1-6])\b", rline):
                            rline = _inject_attr(rline, f'data-file="{ef}" data-l="{bln}"')
                        rendered_raw.append(rline)
                    out.append("\n".join(rendered_raw))
                else:
                    items: list[list[tuple[int, str]]] = []
                    for bln, bline in block_pairs:
                        if ITEM.match(bline):
                            items.append([(bln, ITEM.sub("", bline, 1))])
                        else:
                            items[-1].append((bln, bline.strip()))
                    tag = "ul" if line.startswith("-") else "ol"
                    li_html = "".join(
                        f'<li data-file="{ef}" data-l1="{it[0][0]}" data-l2="{it[-1][0]}">{self._render_item(it, fname)}</li>'
                        for it in items
                    )
                    out.append(f'<{tag} data-file="{ef}" data-l1="{l1}" data-l2="{l2}">{li_html}</{tag}>')
                i = j
                continue
            else:
                para.append((ln, line))
            i += 1

        flush()
        if stack:
            self.errors.append(f"{fname} 末尾有未闭合的 ::: 块")
            for _, open_ln, idx, tag_head in reversed(stack):
                out[idx] = f'{tag_head} data-file="{ef}" data-l1="{open_ln}" data-l2="{off + len(lines)}">'
                out.append("</div>")
        return "\n".join(out)


def _compile_included_file(conv: MarkdownCompiler, inc_path: Path, rel_posix: str) -> str:
    cleaned: list[str] = []
    for idx, line in enumerate(inc_path.read_text(encoding="utf-8").split("\n")):
        if nm := INCLUDE_RE.match(line):
            conv.errors.append(f"{rel_posix}:{idx + 1} 不支持嵌套 include：{nm.group(1)}")
            cleaned.append("")
        else:
            cleaned.append(line)
    return conv.convert("\n".join(cleaned), rel_posix)


def compile_markdown_dir(src_dir: Path) -> tuple[str, list[str]]:
    """将 src_dir 下的 main.md（或旧式 *.md）与文献库编译为完整 doc.html 字符串与错误列表。"""
    root = src_dir.resolve()
    main_path = root / "main.md"
    if not main_path.is_file():
        md_files = sorted(src_dir.glob("*.md"))
        bib_path = src_dir / "refs.bib"
        bib = parse_bib(bib_path.read_text(encoding="utf-8")) if bib_path.exists() else {}
        conv = MarkdownCompiler(bib)
        parts = [conv.convert(f.read_text(encoding="utf-8"), f.name) for f in md_files]
        doc = conv.link_subsections("\n".join(parts)).replace("<!--REFS-->", conv.refs_html())
        return doc, conv.errors

    fm, body, start_ln = parse_frontmatter(main_path.read_text(encoding="utf-8"))
    pre_errors: list[str] = []
    bib_rel = fm.get("bib") or "refs.bib"
    bib_res = resolve_in_src(root, bib_rel)
    bib = {}
    if bib_res is None:
        pre_errors.append(f"main.md: bib 路径越界：{bib_rel}")
    elif bib_res[0].is_file():
        bib = parse_bib(bib_res[0].read_text(encoding="utf-8"))
    elif fm.get("bib") and bib_rel != "refs.bib":
        pre_errors.append(f"main.md: bib 文件不存在：{bib_rel}")

    conv = MarkdownCompiler(bib)
    conv.errors.extend(pre_errors)
    parts: list[str] = []
    chunk: list[str] = []
    chunk_start = start_ln

    def flush_chunk() -> None:
        if any(s.strip() for s in chunk):
            rendered = conv.convert("\n".join(chunk), "main.md", start_line=chunk_start)
            if rendered:
                parts.append(rendered)
        chunk.clear()

    for idx, line in enumerate(body.split("\n")):
        ln = start_ln + idx
        if not (m := INCLUDE_RE.match(line)):
            if not chunk:
                chunk_start = ln
            chunk.append(line)
            continue
        flush_chunk()
        raw_rel = m.group(1)
        resolved = resolve_in_src(root, raw_rel)
        if resolved is None:
            conv.errors.append(f"main.md:{ln} include 路径越界：{raw_rel}")
        elif resolved[0] == main_path:
            conv.errors.append(f"main.md:{ln} 不能自包含 main.md")
        elif not resolved[0].is_file():
            conv.errors.append(f"main.md:{ln} include 文件不存在：{raw_rel}")
        else:
            parts.append(_compile_included_file(conv, resolved[0], resolved[1]))

    flush_chunk()
    doc = conv.link_subsections("\n".join(parts)).replace("<!--REFS-->", conv.refs_html())
    return doc, conv.errors
