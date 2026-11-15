- agent name: claude-fable-5-2
- harness: claude-code
- session: 55ea5180
- time: 2026-11-15 07:36 (Asia/Singapore)

# Claude Code 本地会话适配

实现由 `scripts/claude.py` 适配原始日志，其余流程与 Codex、AGY 共用；代码维护见 [模块职责](architecture.md)。

## 定位来源

`--current --harness claude-code` 从 `CLAUDE_CODE_SESSION_ID` 读取会话 ID。自动查找覆盖 `$CLAUDE_CONFIG_DIR/projects/<项目>/<id>.jsonl`，默认根目录为 `~/.claude`，Desktop 与 CLI 共用该位置。

完整 ID 和至少 8 位的唯一前缀均可使用。会话 ID 以文件名为准；恢复的会话可能带有旧 ID 的记录，不影响绑定。

## 导出范围

| 日志内容 | 处理方式 |
| --- | --- |
| `user` 记录，正文为文本或图片 | 作为一轮的人类 prompt；`<system-reminder>` 等宿主注入片段剔除 |
| `user` 记录，正文为 `tool_result` | 按 `tool_use_id` 配对到对应调用 |
| `assistant` 记录的 `text` | 回复正文；所属消息以 `tool_use` 结束时视为过程说明 |
| `assistant` 记录的 `tool_use` | 工具调用；`Bash`、`Write`、`Edit`、`Read` 转换为渲染器已有的工具名 |
| `assistant` 记录的 `thinking` | 仅导出非空的显示文本；签名与 `redacted_thinking` 不导出 |
| `isMeta`、`isSidechain` 记录 | 不导出；子代理日志位于下一级目录，不参与查找 |
| 压缩摘要、非人类来源的通知 | 作为当前轮的过程说明，不新开一轮 |
| `api-request*`、`attachment`、`file-history-*` 等记账记录 | 不导出 |

以 `[Request interrupted by user` 开头的记录将当前轮标记为中断。同一 `uuid` 的重复记录只处理一次。

## 署名

署名通过 `get_model_name.py --framework claude-code` 生成，模型取自绑定日志中最近一条助手消息；`CLAUDE_CONFIG_DIR` 由日志路径推得，不使用后台进程所属会话的身份。

## 验证

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .agents/skills/tmp/session-map/scripts/tests -p 'test_claude.py' -v
```
