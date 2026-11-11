"""实验工具的确认、路径与输出约定。"""
import json
import os
from pathlib import Path
import shutil

NOTICE = '实验工具：使用前须向用户说明本次动作并取得同意；用户目前不具备 Blender 审核能力。'


def add_confirmation(parser):
    parser.add_argument('--user-confirmed', action='store_true', help=NOTICE)


def require_confirmation(parser, args):
    if not args.user_confirmed:
        parser.error(NOTICE + ' 已取得本次同意后传入 --user-confirmed；该标志不能代替询问。')


def resolve_blender(value='blender'):
    candidate = shutil.which(value)
    if candidate is None:
        candidate = str(Path(value).expanduser().resolve())
    path = Path(candidate)
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError(f'Blender 可执行文件无效：{value}')
    return str(path.resolve())


def write_json(path, value):
    """以独占方式写结果，防止覆盖已有人工作品或检查结果。"""
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
