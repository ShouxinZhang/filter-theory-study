#!/usr/bin/env python3
"""用户侧 Antigravity 升级入口: 查询最新版 -> sudo -n 调用 root 助手安装 -> 改写启动器 -> 清理旧版.

agent 不接触 sudo 密码: 仅当用户已完成一次性 setup (见 --setup) 时 sudo -n 才会成功.
"""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

RELEASES = "https://antigravity-hub-auto-updater-974169037036.us-central1.run.app/releases"
HELPER = "/usr/local/sbin/agy-install"
LAUNCHER = Path.home() / ".local/bin/antigravity"
DEFAULT_PROXY = "http://127.0.0.1:7897"
EXEC_RE = re.compile(r"/opt/antigravity-(\d+\.\d+\.\d+)/antigravity")
HERE = Path(__file__).resolve().parent


def vkey(v):
    return tuple(int(x) for x in v.split("."))


def latest(proxy):
    handlers = [urllib.request.ProxyHandler({"https": proxy, "http": proxy})] if proxy else []
    with urllib.request.build_opener(*handlers).open(RELEASES, timeout=15) as r:
        rels = json.load(r)
    best = max(rels, key=lambda x: vkey(x["version"]))
    return best["version"], str(best["execution_id"])


def current():
    m = EXEC_RE.search(LAUNCHER.read_text()) if LAUNCHER.exists() else None
    return m.group(1) if m else None


def sudo(*args):
    return subprocess.run(["sudo", "-n", HELPER, *args], check=True)


def setup_text():
    user = os.environ.get("USER") or os.getlogin()
    src = HERE / "agy-install.sh"
    return "\n".join([
        "# 一次性配置 (由用户本人在终端执行, 需输入 sudo 密码):",
        f"sudo install -o root -g root -m 0755 {shlex.quote(str(src))} {HELPER}",
        f"echo 'AGY_PROXY={DEFAULT_PROXY}' | sudo tee /etc/default/agy-install >/dev/null",
        f"echo '{user} ALL=(root) NOPASSWD: {HELPER}' | sudo tee /etc/sudoers.d/agy-install >/dev/null",
        "sudo chmod 0440 /etc/sudoers.d/agy-install && sudo visudo -cf /etc/sudoers.d/agy-install",
        "# 修改 agy-install.sh 后需重新执行第一行才会生效.",
    ])


def main():
    ap = argparse.ArgumentParser(description="免密升级 Antigravity 桌面应用")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="仅比较当前与最新版本 (默认)")
    g.add_argument("--apply", action="store_true", help="安装最新版并切换启动器")
    g.add_argument("--setup", action="store_true", help="打印一次性 sudoers 配置命令")
    ap.add_argument("--proxy", default=os.environ.get("https_proxy") or DEFAULT_PROXY)
    a = ap.parse_args()

    if a.setup:
        print(setup_text())
        return 0
    cur = current()
    ver, eid = latest(a.proxy)
    print(f"当前: {cur or 'unknown'}  最新: {ver}")
    if not a.apply:
        return 0
    if cur and vkey(cur) >= vkey(ver):
        print("已是最新, 无需升级")
        return 0
    if subprocess.run(["sudo", "-n", "-l", HELPER], capture_output=True).returncode:
        print("未完成免密配置, 请用户执行:\n" + setup_text(), file=sys.stderr)
        return 2
    sudo("install", ver, eid)
    text = LAUNCHER.read_text()
    if cur:
        shutil.copy2(LAUNCHER, LAUNCHER.with_name(f"antigravity.bak-{cur}"))
        LAUNCHER.write_text(text.replace(f"/opt/antigravity-{cur}/", f"/opt/antigravity-{ver}/"))
    else:
        print(f"警告: 未识别启动器中的版本, 请手动指向 /opt/antigravity-{ver}", file=sys.stderr)
    sudo("prune", ver, *([cur] if cur else []))
    for b in LAUNCHER.parent.glob("antigravity.bak-*"):
        if b.name != f"antigravity.bak-{cur}":
            b.unlink()
    print(f"升级完成: {cur} -> {ver}, 重启 Antigravity 后生效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
