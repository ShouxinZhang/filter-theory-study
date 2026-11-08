"""Render normalized turns as Markdown; no source discovery or subscriptions."""
import json
import os
import re

from models import ts

MAP_TMPL = """# map · {sid8}

<!-- 人写区域, 脚本永不覆盖. 引用原件: [p1](prompts.md#p1) -->

## 主线

- [ ] [p1](prompts.md#p1)

## 支线

- 

## 待办 / 迷失时看这里

- 
"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fence(body, lang=""):
    n = max([3] + [len(m) + 1 for m in re.findall(r"`{3,}", body)])
    f = "`" * n
    return f"{f}{lang}\n{body.rstrip()}\n{f}"


def details(summary, body, open_=False):
    o = " open" if open_ else ""
    return f"<details{o}><summary>{esc(summary)}</summary>\n\n{body.strip()}\n\n</details>"


def user_text(c):
    m = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", c or "", re.S)
    return (m.group(1) if m else (c or "")).strip()


def tool_title(tc):
    a, n = tc.get("args", {}), tc.get("name", "?")
    if n == "run_command":
        return f"Ran {a.get('toolSummary') or 'command'}"
    if n in {"exec", "exec_command", "functions.exec_command", "functions.exec"}:
        return f"Ran {n}"
    p = a.get("Path") or a.get("TargetFile") or ""
    base = os.path.basename(p) if p else ""
    verb = {"write_file": "Wrote", "edit_file": "Edited", "read_file": "Read"}.get(n, n)
    return f"{verb} {base}".strip()


def tool_body(tc, result, assets=None):
    a, n = tc.get("args", {}), tc.get("name", "?")
    result = tc.get("result", result)
    references = set()
    if assets:
        cleaned, refs = assets.extract(json.dumps(a, ensure_ascii=False))
        a = json.loads(cleaned)
        references.update(refs)
        if result:
            result, refs = assets.extract(result)
            references.update(refs)
    if n == "run_command":
        head = fence(a.get("CommandLine", ""), "bash")
    elif n in {"exec", "functions.exec"} and isinstance(a.get("input"), str):
        head = fence(a["input"], "javascript")
    elif n in {"exec_command", "functions.exec_command"}:
        head = fence(a.get("cmd", ""), "bash")
    elif n == "write_file":
        head = f"`{a.get('Path','')}`\n\n" + fence(a.get("Content", ""), "markdown")
    elif n == "edit_file":
        head = (f"`{a.get('Path','')}`\n\n" + fence(a.get("Target", ""), "text")
                + "\n\n→\n\n" + fence(a.get("Replacement", ""), "text"))
    else:
        head = fence(json.dumps(a, ensure_ascii=False, indent=2), "json")
    out = "_(等待输出)_" if tc.get("pending") else "_(无输出)_"
    if result:
        out = fence(result, "text")
    body = f"{head}\n\n{out}"
    return assets.compact_tool(body, references) if assets else body


def thought_label(st, i):
    if st[i].get("thought_label"):
        return st[i]["thought_label"]
    if i + 1 < len(st):
        try:
            dt = max(0, int((ts(st[i + 1]["created_at"]) - ts(st[i]["created_at"])).total_seconds()))
            if dt > 0:
                return f"Thought for {dt}s"
        except Exception:
            pass
    return "Thought"


def render_turn(k, t, assets=None):
    references = set()

    def text(value):
        if not assets:
            return value
        value, refs = assets.extract(value)
        references.update(refs)
        return assets.display_links(assets.display_images(value))

    u = t["user"]
    st = t["steps"]
    when = ts(u["created_at"])
    lines = [f'<a id="p{k}"></a>', "", f"## p{k} · {when:%m-%d %H:%M}", ""]
    txt = esc(text(user_text(u.get("content"))))
    lines += ["> " + (ln + "  " if ln else "") for ln in txt.splitlines()] + [""]
    for m in u.get("media") or []:
        link = f"- 📎 [{os.path.basename(m.get('uri',''))}](file://{m.get('uri','')})"
        lines.append(assets.display_links(link) if assets else link)
    final_i = None
    for i, d in enumerate(st):
        if (d.get("type") == "PLANNER_RESPONSE" and d.get("content")
                and not d.get("tool_calls") and d.get("phase") != "commentary"):
            final_i = i
    inner = []
    for i, d in enumerate(st):
        if i == final_i:
            if d.get("thinking"):
                inner.append(details(thought_label(st, i), esc(text(d["thinking"]))))
            continue
        ty = d.get("type")
        if ty == "PLANNER_RESPONSE":
            if d.get("thinking"):
                inner.append(details(thought_label(st, i), esc(text(d["thinking"]))))
            if d.get("content"):
                inner.append(text(d["content"]))
            for tc in d.get("tool_calls") or []:
                inner.append(details(tool_title(tc), tool_body(tc, "", assets)))
        elif ty == "ERROR_MESSAGE":
            inner.append(details("⚠ Error", fence(text(d.get("error", "")), "text")))
    if st or t.get("status"):
        ended = t.get("ended_at") or t.get("last_activity_at") or (st[-1]["created_at"] if st else u["created_at"])
        dur = t.get("duration_seconds", max(0, int((ts(ended) - when).total_seconds())))
        nt = sum(len(d.get("tool_calls") or []) for d in st)
        status = {"working": "Working", "interrupted": "Interrupted"}.get(t.get("status"), "Worked")
        lines += ["", details(f"{status} for {dur}s · {nt} tools", "\n\n".join(inner) or "_(空)_")]
    if final_i is not None:
        lines += ["", text(st[final_i]["content"].strip())]
    if assets and references:
        lines.append(assets.links(references))
    lines += ["", "---", ""]
    return "\n".join(lines)


def render(sid, src, harness, header, turns, assets=None):
    idx = []
    for k, t in enumerate(turns, 1):
        ut = user_text(t["user"].get("content"))
        first = ut.splitlines()[0][:60] if ut else ""
        if first.startswith("!["):
            first = "图像附件"
        idx.append(f"- [p{k}](#p{k}) {esc(first)}")
    head = (f"{header}\n\n# prompts · {sid[:8]}\n\n"
            f"来源 harness `{harness}`，会话 `{sid}`。\n\n"
            f"<!-- 机械文件, sync.py 自动生成, 勿手改. "
            f"源: {src} · 同步状态见 .sync-state.json -->\n\n"
            + "\n".join(idx) + "\n\n---\n\n")
    return head + "\n".join(render_turn(k, t, assets) for k, t in enumerate(turns, 1))

