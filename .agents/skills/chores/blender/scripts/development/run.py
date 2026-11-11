"""从系统 Python 启动隔离的 Blender 后台任务并保留日志。"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import add_confirmation, require_confirmation, resolve_blender, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', default='blender')
    parser.add_argument('--blend', type=Path)
    parser.add_argument('--script', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, required=True, help='每次任务使用新的目录')
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--threads', type=int, default=4)
    add_confirmation(parser)
    parser.add_argument('script_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    require_confirmation(parser, args)
    if args.timeout <= 0 or args.threads < 1:
        parser.error('timeout 和 threads 必须为正')
    script = args.script.expanduser().resolve()
    if not script.is_file():
        parser.error('任务脚本不存在')
    binary = resolve_blender(args.blender)
    command = [binary, '--background', '--factory-startup', '--disable-autoexec', '--threads', str(args.threads)]
    if args.blend:
        blend = args.blend.expanduser().resolve()
        if not blend.is_file():
            parser.error('工程文件不存在')
        command.append(str(blend))
    extra = args.script_args[1:] if args.script_args[:1] == ['--'] else args.script_args
    # 内置任务脚本也检查确认标志；已确认的 runner 显式传递本次状态。
    if '--user-confirmed' not in extra:
        extra = ['--user-confirmed', *extra]
    command += ['--python-exit-code', '1', '--python', str(script), '--', *extra]
    work = args.work_dir.expanduser().resolve()
    work.mkdir(parents=True, exist_ok=False)
    timed_out = False
    with (work / 'run.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen(command, cwd=work, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            code = process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            code, timed_out = 124, True
    data = {'command': command, 'exit_code': code, 'timed_out': timed_out,
            'work_dir': str(work), 'log': str(work / 'run.log')}
    write_json(work / 'run.json', data)
    print(json.dumps(data, ensure_ascii=False))
    return code if 0 <= code <= 255 else 1


if __name__ == '__main__':
    raise SystemExit(main())
