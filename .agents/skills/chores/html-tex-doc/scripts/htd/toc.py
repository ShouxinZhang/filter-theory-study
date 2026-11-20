"""可折叠目录卡片的 HTML 生成。"""
from __future__ import annotations

def _build_toc_html(toc: list[tuple[int, str, str, str]], lang: str = "zh") -> str:
    """将 [(level 1|2|3, id, num, title), ...] 构建为支持整卡折叠与分章折叠的目录 HTML。"""
    is_en = (lang or "").lower().startswith("en")
    nodes: list[dict[str, object]] = []
    stack: list[dict[str, object]] = []
    for lv, id_, num, title in toc:
        node: dict[str, object] = {"lv": lv, "id": id_, "num": num, "title": title, "children": []}
        while stack and int(stack[-1]["lv"]) >= lv:  # type: ignore[arg-type]
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)  # type: ignore[attr-defined]
        else:
            nodes.append(node)
        stack.append(node)

    def emit_list(items: list[dict[str, object]]) -> str:
        out: list[str] = ["<ol>"]
        for n in items:
            ch: list[dict[str, object]] = n["children"]  # type: ignore[assignment]
            lv = n["lv"]
            item = (
                f'<button type="button" class="toc-item ui-row ui-row--dense" data-target="{n["id"]}">'
                f'<span class="toc-num">{n["num"]}</span><span class="toc-txt">{n["title"]}</span>'
                f"</button>"
            )
            if ch:
                out.append(
                    f'<li class="toc-branch" data-lv="{lv}"><div class="toc-row" data-target-id="{n["id"]}">'
                    f'<button type="button" class="toc-caret" aria-expanded="true" title="折叠或展开子节">▾</button>'
                    f"{item}</div>{emit_list(ch)}</li>"
                )
            else:
                out.append(
                    f'<li class="toc-leaf" data-lv="{lv}"><div class="toc-row" data-target-id="{n["id"]}">'
                    f'<span class="toc-caret-pad"></span>{item}</div></li>'
                )
        out.append("</ol>")
        return "".join(out)

    has_sub = any(lv > 1 for lv, _, _, _ in toc)
    fold_lbl = "Collapse" if is_en else "收起子节"
    exp_lbl = "Expand all" if is_en else "展开全部"
    toc_lbl = "Contents" if is_en else "目录"
    meta_lbl = f"{len(toc)} sections" if is_en else f"共 {len(toc)} 节"
    sub_btns = (
        '<div class="toc-actions">'
        f'<button type="button" class="toc-sub-btn ui-btn ui-btn--sm" data-toc-act="fold-sub" title="仅显示顶层章节">{fold_lbl}</button>'
        f'<button type="button" class="toc-sub-btn ui-btn ui-btn--sm" data-toc-act="expand-all" title="展开全部层级">{exp_lbl}</button>'
        "</div>"
        if has_sub
        else ""
    )
    return (
        '<nav class="toc" id="doc-toc">'
        '<div class="toc-head">'
        '<button type="button" class="toc-toggle" aria-expanded="true" title="点击折叠或展开目录卡片">'
        '<span class="toc-toggle-icon">▾</span>'
        f"<strong>{toc_lbl}</strong>"
        f'<span class="toc-meta">{meta_lbl}</span>'
        "</button>"
        f"{sub_btns}"
        "</div>"
        f'<div class="toc-body">{emit_list(nodes)}</div>'
        "</nav>"
    )
