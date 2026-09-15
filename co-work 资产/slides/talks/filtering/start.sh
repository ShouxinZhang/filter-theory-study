#!/usr/bin/env bash
# Usage: ./start.sh [port] [Slidev options], for example ./start.sh 3031
set -euo pipefail

talk_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
  talk_port="$1"
  shift
  set -- --port "$talk_port" "$@"
fi
exec node "$talk_dir/../../scripts/talk.mjs" dev "$(basename -- "$talk_dir")" "$@"
