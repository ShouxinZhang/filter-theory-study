"""只读检查指定 Blender 和本机常见配置目录。"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import add_confirmation, require_confirmation, resolve_blender, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', default='blender')
    parser.add_argument('--output', help='可选 JSON 输出；省略时只打印')
    add_confirmation(parser)
    args = parser.parse_args()
    require_confirmation(parser, args)
    binary = resolve_blender(args.blender)
    result = subprocess.run([binary, '--version'], capture_output=True, text=True, timeout=30, check=True)
    home = Path.home()
    roots = [home / '.config/blender', home / '.var/app/org.blender.Blender/config/blender']
    data = {'binary': binary, 'version': result.stdout.splitlines()[0],
            'path_entry': shutil.which(args.blender),
            'config_candidates': [str(p) for root in roots if root.exists() for p in sorted(root.iterdir()) if p.is_dir()],
            'package_evidence': {}}
    # 查询包管理器仅作来源线索；可执行路径与包记录需结合判断。
    for tool, command in [('flatpak', ['flatpak', 'info', '--user', 'org.blender.Blender']),
                          ('dpkg-query', ['dpkg-query', '-S', binary])]:
        if shutil.which(tool):
            check = subprocess.run(command, capture_output=True, text=True, timeout=20)
            data['package_evidence'][tool] = {'exit_code': check.returncode, 'stdout': check.stdout.strip()}
    if args.output:
        write_json(args.output, data)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
