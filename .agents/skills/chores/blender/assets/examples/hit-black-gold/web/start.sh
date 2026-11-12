#!/usr/bin/env bash
# 本地启动入口，可用第一个参数指定端口。
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
port="${1:-8841}"
printf '打开 http://127.0.0.1:%s ，按 Ctrl+C 停止。\n' "$port"
exec python3 -m http.server "$port" --bind 127.0.0.1
