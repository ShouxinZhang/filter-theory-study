"""安装本地已取得校验值的 Blender 官方压缩包，可选迁移配置与切换命令。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import add_confirmation, require_confirmation, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--sha256', required=True, help='从可信官方渠道独立取得的校验值')
    parser.add_argument('--version', required=True, help='完整版本号，例如 5.3.0')
    parser.add_argument('--install-root', type=Path, default=Path.home() / '.local/opt')
    parser.add_argument('--profile-from', type=Path)
    parser.add_argument('--profile-to', type=Path)
    parser.add_argument('--activate', action='store_true', help='将 launcher 切换为新版本的符号链接')
    parser.add_argument('--launcher', type=Path, default=Path.home() / '.local/bin/blender')
    add_confirmation(parser)
    args = parser.parse_args()
    require_confirmation(parser, args)
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.version):
        parser.error('version 应为完整三段数字版本号')
    if not re.fullmatch(r'[0-9a-fA-F]{64}', args.sha256):
        parser.error('sha256 应为 64 位十六进制值')
    if bool(args.profile_from) != bool(args.profile_to):
        parser.error('profile-from 与 profile-to 须同时提供')
    archive = args.archive.expanduser().resolve(strict=True)
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != args.sha256.lower():
        parser.error('压缩包 SHA-256 与指定值不一致')
    root = args.install_root.expanduser().resolve()
    destination = root / ('blender-' + args.version)
    if destination.exists() or destination.is_symlink():
        parser.error('目标安装目录已存在，请先人工检查')
    # launcher 保留最后一段符号链接，避免 resolve() 将其变成旧版本可执行文件。
    launcher = Path(os.path.abspath(args.launcher.expanduser()))
    if args.activate and launcher.is_relative_to(destination):
        parser.error('命令链接须位于安装包目录之外')
    previous = os.readlink(launcher) if launcher.is_symlink() else None
    if args.activate and launcher.exists() and not launcher.is_symlink():
        parser.error('launcher 已有普通文件，保留该文件并停止')
    profile_from = args.profile_from.expanduser().resolve() if args.profile_from else None
    profile_to = args.profile_to.expanduser().absolute() if args.profile_to else None
    if profile_from and (not profile_from.is_dir() or profile_to.exists() or profile_to.is_symlink()):
        parser.error('配置来源须存在，目标配置目录须不存在')
    if profile_from and (profile_to.is_relative_to(profile_from) or profile_from.is_relative_to(profile_to)
                         or profile_to.is_relative_to(destination) or destination.is_relative_to(profile_to)):
        parser.error('源配置、目标配置与安装目录须相互独立')
    root.mkdir(parents=True, exist_ok=True)
    installed = copied_profile = activated = False
    temporary_link = None
    try:
        with tempfile.TemporaryDirectory(prefix='.blender-stage-', dir=root) as staging:
            with tarfile.open(archive) as package:
                package.extractall(staging, filter='data')
            children = list(Path(staging).iterdir())
            if len(children) != 1 or not children[0].is_dir() or not (children[0] / 'blender').is_file():
                raise ValueError('压缩包应包含单个 Blender 安装目录')
            result = subprocess.run([str(children[0] / 'blender'), '--version'], check=True,
                                    capture_output=True, text=True, timeout=30)
            version_line = result.stdout.splitlines()[0]
            if version_line != 'Blender ' + args.version:
                raise ValueError('包内版本不匹配：' + version_line)
            children[0].rename(destination)
            installed = True
        if profile_from:
            copied_profile = True
            shutil.copytree(profile_from, profile_to, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        if args.activate:
            launcher.parent.mkdir(parents=True, exist_ok=True)
            temporary_link = launcher.parent / ('.blender-link-' + uuid.uuid4().hex)
            temporary_link.symlink_to(destination / 'blender')
            os.replace(temporary_link, launcher)
            activated = True
        data = {'version': args.version, 'sha256': digest, 'binary': str(destination / 'blender'),
                'launcher': str(launcher) if activated else None, 'previous_launcher_target': previous,
                'profile_from': str(profile_from) if profile_from else None,
                'profile_to': str(profile_to) if profile_to else None,
                'rollback': '保留旧安装；需要回退时先询问用户，再按 previous_launcher_target 恢复命令链接。'}
        write_json(destination / 'installation.json', data)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except BaseException:
        # 仅撤回本次新建的目标；旧安装和源配置始终保留。
        if activated:
            if previous is None:
                launcher.unlink()
            else:
                restore = launcher.parent / ('.blender-restore-' + uuid.uuid4().hex)
                restore.symlink_to(previous)
                os.replace(restore, launcher)
        if copied_profile and profile_to.exists():
            shutil.rmtree(profile_to)
        if installed:
            shutil.rmtree(destination)
        raise
    finally:
        if temporary_link and temporary_link.is_symlink():
            temporary_link.unlink()


if __name__ == '__main__':
    main()
