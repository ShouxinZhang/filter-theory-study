"""初始化新版地图路径，并在迁移前保留旧地图原文。"""
import hashlib
import os
import tempfile
import re
from urllib.parse import urlsplit

from render import MAP_TMPL


def map_path(directory):
    """统一供初始化与查询接口使用的地图入口。"""
    return directory / "map" / "map.md"


def rebase_links(text):
    """地图下移一级后修正 Markdown 相对链接，保留代码中的示例。"""
    def target(value):
        bare = value[1:-1] if value.startswith("<") else value
        if not bare or bare.startswith(("/", "#")) or urlsplit(bare).scheme:
            return value
        return "<../" + bare + ">" if value.startswith("<") else "../" + value

    # 围栏代码和行内代码保持原样；其他片段修正内联链接与引用式链接。
    chunks = re.split(r"(```[\s\S]*?```|~~~[\s\S]*?~~~|`+[^`\n]*`+)", text)
    for index in range(0, len(chunks), 2):
        chunks[index] = re.sub(
            r'(\]\()(<[^>]+>|[^\s)]+)',
            lambda match: match[1] + target(match[2]), chunks[index])
        chunks[index] = re.sub(
            r'(^ {0,3}\[[^\]\n]+\]:\s*)(<[^>]+>|\S+)',
            lambda match: match[1] + target(match[2]), chunks[index], flags=re.M)
    return "".join(chunks)


def create_exclusive(path, content):
    """仅初始化缺失文件，保留已有人工内容（包括空文件）。"""
    descriptor, temporary = tempfile.mkstemp(prefix=".map-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        try:
            os.link(temporary, path)
            return True
        except FileExistsError:
            return False
    finally:
        os.unlink(temporary)


def ensure_map(directory, header, sid):
    """调用方持有 session 锁；旧版原文备份成功后才移除旧入口。"""
    destination = map_path(directory)
    destination.parent.mkdir(parents=True, exist_ok=True)
    legacy = directory / "map.md"
    original = legacy.read_bytes() if legacy.is_file() else None
    if original is not None:
        backup_dir = directory / "assets" / "legacy-map"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / (hashlib.sha256(original).hexdigest() + ".md")
        create_exclusive(backup, original)
        if backup.read_bytes() != original:
            raise ValueError(f"旧地图备份校验失败：{backup}")
        content = rebase_links(original.decode("utf-8")).encode("utf-8")
    else:
        content = (header + "\n\n" + MAP_TMPL.format(sid8=sid[:8])).encode("utf-8")
    create_exclusive(destination, content)
    # 若有编辑器同时保存旧文件，留待下次同步备份该版本。
    if original is not None and legacy.read_bytes() == original:
        legacy.unlink()
    return destination
