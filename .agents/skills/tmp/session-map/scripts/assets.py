"""Keep binary payloads and large tool transcripts out of the reading document."""

import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import quote, unquote, urlsplit


DATA_URI = re.compile(r"data:([\w.+-]+/[\w.+-]+);base64,([A-Za-z0-9+/=]+(?:\\/[A-Za-z0-9+/=]*)*)(?![\w+/=])")
EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
              "image/webp": ".webp", "image/svg+xml": ".svg", "image/avif": ".avif",
              "audio/mpeg": ".mp3", "audio/wav": ".wav", "video/mp4": ".mp4"}
TOOL_LIMIT = 16 * 1024
LINE_LIMIT = 4096
IMAGE_LINK = re.compile(r'!\[([^\]\n]*)\]\((<[^>\n]+>|(?:[^()\n]|\([^()\n]*\))+)\)')
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif", ".bmp"}
LOCAL_LINK = re.compile(r'(?<!!)\[([^\]\n]*)\]\((<[^>\n]+>|(?:[^()\n]|\([^()\n]*\))+)\)')


def rewrite_prose(text, transform):
    """Apply a Markdown rewrite outside fenced and inline code."""
    lines, fence = [], None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            lines.append(line)
        elif fence:
            lines.append(line)
        else:
            parts = re.split(r"(`+[^`\n]*`+)", line)
            lines.append("".join(part if i % 2 else transform(part)
                                 for i, part in enumerate(parts)))
    return "".join(lines)


class AssetStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.local_images = {}

    def image_path(self, target):
        """Archive explicitly referenced local images, never fetch remote URLs."""
        if target.startswith("assets/media/"):
            return target
        parsed = urlsplit(target)
        if parsed.scheme not in {"", "file"} or parsed.netloc:
            return None
        path = Path(unquote(parsed.path))
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            return None
        if not path.is_absolute():
            path = self.directory / path
        try:
            stat = path.stat()
            key = (str(path), stat.st_mtime_ns, stat.st_size)
            if key not in self.local_images:
                self.local_images[key] = self.put(path.read_bytes(), "media", path.suffix.lower())
            return self.local_images[key]
        except OSError:
            return None

    def display_images(self, text):
        """Rewrite visible Markdown images; leave code examples untouched."""
        def replace(match):
            target = match[2]
            if target.startswith("<"):
                target = target[1:-1]
            path = self.image_path(target)
            return f"![{match[1]}]({path})" if path else match[0]

        return rewrite_prose(text, lambda part: IMAGE_LINK.sub(replace, part))

    def display_links(self, text):
        """Markdown previews reject file: URLs; use encoded archive-relative URLs.

        Keep source transcripts and code examples intact. Non-local URLs, including
        file://server shares, retain their original semantics.
        """
        def replace(match):
            target, title = match[2].strip(), ""
            titled = re.fullmatch(r"""(.*?)(\s+(?:"[^"\n]*"|'[^'\n]*'))""", target)
            if titled:
                target, title = titled.groups()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            try:
                parsed = urlsplit(target)
            except ValueError:
                return match[0]
            if parsed.scheme.lower() != "file" or parsed.netloc not in {"", "localhost"}:
                return match[0]
            path = Path(unquote(parsed.path))
            if not path.is_absolute():
                return match[0]
            relative = quote(os.path.relpath(path, self.directory), safe="/.-_~")
            if parsed.query:
                relative += "?" + quote(parsed.query, safe="%=&/:?+,-._~")
            if parsed.fragment:
                relative += "#" + quote(parsed.fragment, safe="%-._~")
            return f"[{match[1]}]({relative}{title})"

        return rewrite_prose(text, lambda part: LOCAL_LINK.sub(replace, part))

    def put(self, data, folder, suffix):
        digest = hashlib.sha256(data).hexdigest()
        relative = Path("assets") / folder / (digest + suffix)
        path = self.directory / relative
        # Content-addressed files are immutable; repeated exports do not touch them.
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".asset-", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
        return relative.as_posix()

    def binary(self, encoded, mime):
        try:
            data = base64.b64decode(encoded.replace("\\/", "/"), validate=True)
        except (ValueError, binascii.Error):
            return None
        return self.put(data, "media", EXTENSIONS.get(mime.lower(), ".bin"))

    def extract(self, text):
        references = set()

        def replace(match):
            path = self.binary(match[2], match[1])
            if path is None:
                return match[0]
            references.add(path)
            return path

        text = DATA_URI.sub(replace, text)
        # MCP image blocks can contain bare base64 rather than a data URI.
        if text.lstrip().startswith(("{", "[")) and '"mimeType"' in text:
            def visit(value):
                if isinstance(value, dict):
                    if (value.get("type") in {"image", "audio"}
                            and isinstance(value.get("data"), str)
                            and isinstance(value.get("mimeType"), str)):
                        path = self.binary(value["data"], value["mimeType"])
                        if path:
                            references.add(path)
                            return {**{k: visit(v) for k, v in value.items() if k != "data"},
                                    "asset_path": path}
                    return {k: visit(v) for k, v in value.items()}
                if isinstance(value, list):
                    return [visit(v) for v in value]
                return value
            try:
                value = json.loads(text)
                cleaned = visit(value)
                if cleaned != value:
                    text = json.dumps(cleaned, ensure_ascii=False, indent=2)
            except (ValueError, RecursionError):
                pass
        return text, references

    @staticmethod
    def links(references):
        return "\n\n" + "\n".join(
            f"- [附件 {Path(path).name[:12]}]({path})" for path in sorted(references)
        ) if references else ""

    def compact_tool(self, body, references=()):
        """body is already sanitized; full text remains lossless in a sidecar."""
        if (len(body.encode("utf-8")) <= TOOL_LIMIT
                and all(len(line) <= LINE_LIMIT for line in body.splitlines())):
            return body + self.links(references)
        path = self.put(body.encode("utf-8"), "tool-output", ".txt")
        # A dedicated fence keeps truncated JSON/Markdown from breaking <details>.
        preview = "\n".join(body[:2000].splitlines()[:30])
        fence = "`" * max([3] + [len(m) + 1 for m in re.findall(r"`{3,}", preview)])
        return (f"[完整工具记录 · {len(body.encode('utf-8')):,} bytes]({path})\n\n"
                f"{fence}text\n{preview}\n…（预览截断）\n{fence}"
                + self.links(references))
