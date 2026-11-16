"""监听源目录并重建，维护实时状态。"""
from __future__ import annotations

import threading
import time
from pathlib import Path

from ..build import build_project

class LiveState:
    def __init__(self, src_dir: Path, build_dir: Path, out_dir: Path):
        self.src_dir = src_dir.resolve()
        self.build_dir = build_dir.resolve()
        self.out_dir = out_dir.resolve()
        self.cond = threading.Condition()
        self.wakeup = threading.Event()
        self.v = 0
        self.err = ""
        self.body_html = ""
        self.changed: list[str] = []

    def snapshot_mtimes(self) -> dict[str, int]:
        out: dict[str, int] = {}
        try:
            for p in self.src_dir.rglob("*"):
                if p.is_file() and not p.name.startswith("."):
                    rel = p.relative_to(self.src_dir).as_posix()
                    out[rel] = p.stat().st_mtime_ns
        except OSError:
            pass
        return out


def _watch_loop(state: LiveState, force_first: bool) -> None:
    prev: dict[str, int] | None = None
    first = True
    while True:
        cur = state.snapshot_mtimes()
        if prev is None or cur != prev:
            changed = [] if prev is None else sorted(k for k, v in cur.items() if prev.get(k) != v)
            prev = cur
            t0 = time.time()
            try:
                rc, msg, body = build_project(
                    state.src_dir,
                    state.build_dir,
                    state.out_dir,
                    force=(force_first and first),
                )
                first = False
                err = msg if rc != 0 else ""
            except Exception as e:
                rc, err, body = 1, f"{type(e).__name__}: {e}", ""
            with state.cond:
                state.v += 1
                state.err = err
                if rc == 0:
                    state.body_html = body
                state.changed = changed
                state.cond.notify_all()
            dt = (time.time() - t0) * 1000
            stamp = time.strftime("%H:%M:%S")
            if err:
                print(f"[{stamp}] 构建失败（{dt:.0f} ms）\n{err}", flush=True)
            else:
                ch_info = f" [{', '.join(changed[:3])}]" if changed else ""
                print(f"[{stamp}] 已刷新 v={state.v}（{dt:.0f} ms）{ch_info}", flush=True)
        state.wakeup.wait(timeout=0.25)
        state.wakeup.clear()
