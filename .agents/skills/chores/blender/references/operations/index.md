- agent name: gpt-6-astra
- harness: codex
- session: 01a1cb71
- time: 2026-11-12 06:39 (Asia/Shanghai)

# 运维实验模块

先遵循 [使用前约定](../../SKILL.md)。以下工具当前面向 Linux，安装工具接收本地压缩包。

| 工具 | 输入与行为 |
| --- | --- |
| `scripts/operations/inspect_env.py` | `--blender` 指定可执行文件；打印版本、配置路径和包管理器线索，可用 `--output` 保存 JSON。 |
| `scripts/operations/install_release.py` | `--archive`、`--sha256`、`--version`；校验后安装到 `--install-root`，默认 `~/.local/opt`。 |

安装包和校验值须从可信官方发布渠道取得并核对目标平台。SHA-256 检查保证文件与给定值一致，来源真实性仍需核验。
安装目录已有内容时停止；解包在临时目录进行，确认包内版本后再发布。`installation.json` 保存本次参数与回退线索。
`--profile-from` 和 `--profile-to` 成对指定，源目录保留，目标应为空缺路径；配置跨版本兼容性需后续检查。
`--activate` 可切换 `--launcher` 符号链接；普通文件会阻止切换，旧安装保留。桌面入口与系统文件关联由单独任务处理。

所有执行命令在获得本次授权后加 `--user-confirmed`。先查看 `--help`，再提供本次明确路径；完整的真实版本升级属于待验证范围。
