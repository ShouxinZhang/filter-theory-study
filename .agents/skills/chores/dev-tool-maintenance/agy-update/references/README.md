# agy-update 参考细则

## 安装布局

| 路径 | 所有者 | 作用 |
| --- | --- | --- |
| `/opt/antigravity-X.Y.Z/` | root | 各版本本体 (官方 `Antigravity.tar.gz` 解压) |
| `~/.local/bin/antigravity` | 用户 | 启动器, `exec /opt/antigravity-X.Y.Z/antigravity`, 带代理参数 |
| `~/.local/bin/antigravity-desktop` | 用户 | 桌面入口, 经 systemd-run 调用上面的启动器 |
| `~/.local/bin/antigravity.bak-<旧版>` | 用户 | 上一版启动器备份 |
| `/usr/local/sbin/agy-install` | root | root 助手 (来自 `scripts/agy-install.sh`) |
| `/etc/sudoers.d/agy-install` | root 0440 | 仅对该助手 NOPASSWD |
| `/etc/default/agy-install` | root | 可选, `AGY_PROXY=...` |

版本列表接口: `https://antigravity-hub-auto-updater-974169037036.us-central1.run.app/releases`,
返回 `[{version, execution_id}]`; 下载地址
`https://storage.googleapis.com/antigravity-public/antigravity-hub/<ver>-<id>/linux-x64/Antigravity.tar.gz`.

## 安全模型

- 密码只由用户在一次性 setup 时输入; agent 只用 `sudo -n`, 未配置时直接失败, 不提示输入密码.
- 助手只接受 `install <ver> <id>` 和 `prune <keep...>` 两种参数, 参数都按正则校验, 下载地址的域名与路径前缀写死.
- 压缩包需全部位于 `Antigravity-x64/` 下, 主程序必须是 ELF, 先解压到 `.partial` 再原子改名.
- 助手源文件位于仓库内 (用户可写), 但生效的是 root 所有的副本; 修改仓库源文件不会自动提权.
- 官方未提供校验和, 完整性依赖 HTTPS 与固定的下载源.

## 回滚

```bash
cp ~/.local/bin/antigravity.bak-<旧版> ~/.local/bin/antigravity   # 旧版目录仍保留在 /opt
```

## 撤销免密

```bash
sudo rm /etc/sudoers.d/agy-install /usr/local/sbin/agy-install /etc/default/agy-install
```
