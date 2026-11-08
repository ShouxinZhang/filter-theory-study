#!/usr/bin/env python3
"""Stable session-map CLI: sync, subscribe/unsubscribe, inspect, and watch."""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import runtime
from sources import current_session


def manage(argv):
    command = argv[0]
    parser = argparse.ArgumentParser(prog=f'sync.py {command}', description='查询和管理会话订阅')
    parser.add_argument('--json', action='store_true', help='输出机器可读 JSON')
    parser.add_argument('--output-root', type=Path)
    parser.add_argument('--harness', choices=('auto', 'codex', 'antigravity'), default='auto')
    if command == 'list':
        parser.add_argument('--all', action='store_true', help='同时列出已退订的会话')
    else:
        parser.add_argument('sid', nargs='?', help='完整会话 ID 或唯一前缀')
        parser.add_argument('--current', action='store_true')
    if command == 'subscribe':
        parser.add_argument('--source', type=Path)
    args = parser.parse_args(argv[1:])
    if args.output_root:
        runtime.SESS = args.output_root.expanduser().resolve()
    try:
        watcher = runtime.watcher_status()
        if command == 'list':
            items = [runtime.subscription_info(directory, watcher)
                     for directory in sorted(runtime.SESS.glob('*/'))
                     if directory.is_dir() and (args.all or runtime.subscribed(directory))]
            items = [item for item in items if args.harness in {'auto', item['harness']}]
            result = {'watcher': watcher, 'subscriptions': items}
        else:
            if args.current:
                if args.sid or getattr(args, 'source', None):
                    raise ValueError('--current 与 ID / --source 不能同时指定')
                args.harness, args.sid = current_session(args.harness)
            if command == 'subscribe':
                source = runtime.resolve_source(args.sid, args.harness, args.source)
                runtime.sync_source(source, subscribe=True)
                directory = runtime.SESS / source.sid
            else:
                if not args.sid:
                    raise ValueError('需要会话 ID 或 --current')
                directory = runtime.subscription_directory(args.sid)
                if args.harness != 'auto' and runtime.subscription_info(directory)['harness'] != args.harness:
                    raise ValueError('订阅的 harness 与请求不符')
                if command == 'unsubscribe':
                    runtime.unsubscribe(directory.name)
            result = {'watcher': runtime.watcher_status(), 'subscription': runtime.subscription_info(directory)}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"watcher={result['watcher']['status']}")
            items = result.get('subscriptions', [result.get('subscription')])
            for item in items:
                print(f"{item['id']}  {item['harness']}  subscribed={item['subscribed']}  "
                      f"watching={item['watching']}  {item['sync_status']}  {item['name']}")
                if command != 'list':
                    print(json.dumps(item, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as error:
        if args.json:
            print(json.dumps({'error': str(error)}, ensure_ascii=False))
        else:
            print(f'error: {error}', file=sys.stderr)
        return 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in {'list', 'show', 'subscribe', 'unsubscribe'}:
        return manage(argv)
    ap = argparse.ArgumentParser(description='session-map 同步与监听工具；支持 list/show/subscribe/unsubscribe 子命令')
    ap.add_argument('sid', nargs='?', help='会话 ID 或前缀 (支持前 8 位)')
    ap.add_argument('--harness', choices=('auto', 'antigravity', 'codex'), default='auto')
    ap.add_argument('--current', action='store_true', help='从当前 harness 的会话环境变量取得 ID')
    ap.add_argument('--source', type=Path, help='显式指定本地 JSONL 日志')
    ap.add_argument('--output-root', type=Path, help='覆盖归档根目录，用于隔离测试或导出')
    ap.add_argument('--all', action='store_true', help='单次同步全部已订阅会话')
    ap.add_argument('--watch', action='store_true', help='常驻轮询已订阅会话')
    ap.add_argument('-i', '--interval', type=float, default=1.0, help='轮询间隔秒数 (默认 1.0)')
    ap.add_argument('--install-service', action='store_true', help='安装并启动 systemd --user 服务')
    ap.add_argument('--status-service', action='store_true', help='查看 systemd --user 服务状态')
    a = ap.parse_args(argv)
    if a.output_root:
        runtime.SESS = a.output_root.expanduser().resolve()
    if a.interval <= 0:
        ap.error('--interval 必须大于 0')
    if a.current:
        if a.sid or a.source:
            ap.error('--current 与 ID / --source 不能同时指定')
        try:
            a.harness, a.sid = current_session(a.harness)
        except ValueError as error:
            ap.error(str(error))
    if a.install_service:
        runtime.install_service()
    elif a.status_service:
        runtime.status_service()
    elif a.watch:
        runtime.watch(a.interval)
    elif a.all:
        return 0 if runtime.sync_all() else 1
    elif a.sid or a.source:
        try:
            runtime.sync(a.sid, a.harness, a.source)
        except (OSError, ValueError, KeyError) as error:
            ap.exit(1, f'error: {error}\n')
    else:
        ap.error('需要 <id>、--all、--watch、--install-service 或 --status-service')


if __name__ == "__main__":
    sys.exit(main())
