---
name: agy-update
description: 免密静默升级 Antigravity (agy) 桌面应用: 查询最新版本, 经 sudoers 白名单的 root 脚本下载校验安装到 /opt, 保留上一版本.
---

# agy-update

## 速查

```bash
S=.agents/skills/chores/agy-update/scripts/agy_update.py
python3 $S --check    # 对比当前 / 最新版本
python3 $S --apply    # 免密安装最新版, 切换启动器, 清理更早版本
python3 $S --setup    # 打印一次性 sudoers 配置命令 (交给用户执行)
```

## 流程

1. `--check` 查看是否有新版本; 有则 `--apply`.
2. `--apply` 返回码 2 表示未完成免密配置: 把 `--setup` 的输出交给用户亲手执行, **不得索要或使用明文 sudo 密码**.
3. 完成后提示用户重启 Antigravity; 当前会话所用的旧版本保留, 用于回滚.
4. 按 tmp/task 规范在 `.agents/.tmp/task/YYYY-MM/<日期>_antigravity-update/docs/logs/` 记录一次升级.

## 约束

- root 侧只放行 `/usr/local/sbin/agy-install` (root:root 0755); 修改 `scripts/agy-install.sh` 后需用户重新 `install` 才生效.
- 下载源固定为 `storage.googleapis.com/antigravity-public`, 参数按正则校验, 安装后 `chrome-sandbox` 设为 4755.
- 只保留新版与上一版; 运行中的版本不删.

## 参考

- [references/README.md](references/README.md): 安装布局, 安全模型与回滚.
