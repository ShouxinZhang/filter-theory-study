#!/usr/bin/env bash
# agy-install: root 侧 Antigravity 安装助手, 部署到 /usr/local/sbin/agy-install (root:root 0755),
# 由 /etc/sudoers.d/agy-install 对单一用户 NOPASSWD 放行. 参数严格校验, 下载源固定.
#   agy-install install <version> <execution_id>   下载并安装到 /opt/antigravity-<version>
#   agy-install prune <keep1> [keep2]              删除其余 /opt/antigravity-X.Y.Z (运行中的跳过)
set -euo pipefail
umask 022
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

CONF=/etc/default/agy-install   # 可选, root 所有; 例: AGY_PROXY=http://127.0.0.1:7897
AGY_PROXY=""
[[ -f $CONF && $(stat -c %u "$CONF") == 0 ]] && . "$CONF"

VER_RE='^[0-9]+\.[0-9]+\.[0-9]+$'
die() { echo "agy-install: $*" >&2; exit 1; }
[[ $EUID -eq 0 ]] || die "需以 root 运行 (sudo -n /usr/local/sbin/agy-install ...)"

running() { pgrep -f "^/opt/antigravity-$1/" >/dev/null; }

cmd_install() {
    local ver=$1 id=$2
    [[ $ver =~ $VER_RE ]] || die "非法版本号: $ver"
    [[ $id =~ ^[0-9]{6,24}$ ]] || die "非法 execution_id: $id"
    local dest=/opt/antigravity-$ver
    [[ -x $dest/antigravity ]] && { echo "已安装: $dest"; return 0; }
    local url="https://storage.googleapis.com/antigravity-public/antigravity-hub/$ver-$id/linux-x64/Antigravity.tar.gz"
    tmp=$(mktemp -d /tmp/agy-install.XXXXXX)
    trap 'rm -rf "${tmp:-}"' EXIT
    local px=(); [[ -n $AGY_PROXY ]] && px=(--proxy "$AGY_PROXY")
    curl -fsSL --proto '=https' --retry 3 "${px[@]}" -o "$tmp/a.tgz" "$url" || die "下载失败: $url"
    tar -tzf "$tmp/a.tgz" | grep -qvE '^Antigravity-x64/' && die "压缩包含意外路径"
    tar -xzf "$tmp/a.tgz" -C "$tmp" --no-same-owner
    local src=$tmp/Antigravity-x64
    file -b "$src/antigravity" | grep -q '^ELF 64-bit' || die "主程序不是 ELF"
    [[ -f $src/chrome-sandbox ]] || die "缺少 chrome-sandbox"
    rm -rf "$dest.partial"; mv "$src" "$dest.partial"
    chown -R root:root "$dest.partial"; chmod 4755 "$dest.partial/chrome-sandbox"
    mv "$dest.partial" "$dest"
    echo "已安装: $dest"
}

cmd_prune() {
    local keep=("$@") d v
    for v in "${keep[@]}"; do [[ $v =~ $VER_RE ]] || die "非法版本号: $v"; done
    for d in /opt/antigravity-*; do
        v=${d#/opt/antigravity-}
        [[ $v =~ $VER_RE ]] || continue
        [[ " ${keep[*]} " == *" $v "* ]] && continue
        if running "$v"; then echo "跳过 (运行中): $d"; continue; fi
        rm -rf -- "$d"; echo "已删除: $d"
    done
}

case "${1:-}" in
    install) [[ $# -eq 3 ]] || die "用法: install <version> <execution_id>"; cmd_install "$2" "$3" ;;
    prune)   [[ $# -ge 2 && $# -le 3 ]] || die "用法: prune <keep1> [keep2]"; shift; cmd_prune "$@" ;;
    *) die "用法: install <version> <execution_id> | prune <keep1> [keep2]" ;;
esac
