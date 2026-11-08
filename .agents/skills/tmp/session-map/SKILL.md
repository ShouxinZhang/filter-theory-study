---
name: session-map
description: 为 Antigravity 与 Codex App/CLI 的本地长会话建立讨论主题树 (map.md) 与渐进折叠记录 (prompts.md)，按会话 ID 存放在 .agents/.tmp/session/。支持基于当前上下文维护讨论树、订阅查询和详情、订阅/退订管理、公开推理摘要和工具输出、后台热同步。
---

# session-map

在 `.agents/.tmp/session/<id>/` 下维护讨论树、记录及附件。
- `map.md` 由用户与 agent 协作维护讨论主线、支线和待办，用 `[pN](prompts.md#pN)` 引用对应轮次。同步脚本仅在文件缺失时生成模板，已有内容始终保留。
- `prompts.md` 由本地日志机械生成，通过 `<details>` 折叠过程和工具输出，最终回复在外层显示。
- 图片等二进制附件按内容哈希存入 `assets/media/`，不嵌入 Base64。用户和助手正文的图片通过相对路径显示；工具输出中的图片保留按需打开的链接。超长工具记录存入 `assets/tool-output/`，正文保留短预览和完整记录链接；读取细节时再打开对应附件。
- Antigravity 读取 `~/.gemini/antigravity/brain/<id>/.system_generated/logs/transcript_full.jsonl`。
- Codex 读取 `${CODEX_HOME:-~/.codex}/sessions/` 或 `archived_sessions/` 的 `rollout-*.jsonl`，支持 Desktop 与 CLI。推理仅导出公开 `summary`，不导出原始思维链或加密内容。

## 速查

```bash
S=.agents/skills/tmp/session-map/scripts/sync.py

# 列出当前订阅，查询指定会话详情，JSON 可由 agent 直接消费
python3 $S list --json
python3 $S show <session-id或前8位> --json

# 在 Codex 会话中订阅当前聊天
python3 $S subscribe --harness codex --current --json

# 退订并保留已有文档，list --all 可同时查看已退订会话
python3 $S unsubscribe <session-id或前8位> --json
python3 $S list --all --json

# 显式日志路径，适合自动查找不到的本地日志
python3 $S subscribe --harness codex --source /absolute/path/rollout-example.jsonl

# 同步所有已订阅的 Antigravity / Codex 会话
python3 $S --all

# Linux 上安装并启动后台监听服务，启用后每秒检查一次
python3 $S --install-service
python3 $S --status-service
```

## 工作流

- 用户问“哪些 session 在订阅”“订阅详情”时，先调用 `list --json` 或 `show ID --json`，依据输出回答。单独区分 `subscribed`、`watching` 和 `sync_status`，不能仅凭目录存在判断正在同步。
- 用户要求订阅/退订时调用对应命令。`unsubscribe` 停止后续同步并保留文档，`subscribe` 可重新启用。旧式 `sync.py ID` 和 `--current` 仍等价于订阅并同步。
- 首次同步会保存 `.source.json`，后续 `--all` 和 `--watch` 读取同一来源。原有 Antigravity 目录可直接沿用。
- 署名根据绑定的源会话生成，模型取日志最后记录值，后台服务可独立于当前聊天环境运行。
- `--current` 读取 `CODEX_THREAD_ID` 或 `ANTIGRAVITY_CONVERSATION_ID`。无法唯一识别时指定 harness 和 ID。
- `--watch` 每秒检查已订阅日志的修改时间和大小，有更新时重新生成；正文实质内容变化时才原子替换 `prompts.md`，仅同步时间变化不触发重写。附件不变则不重写。脚本升级后需重启已有服务以加载新代码。
- 删除会话归档目录即可停止该会话的追踪。
- 用户要求维护 `map.md` 时，默认基于当前上下文直接整理，按需读取现有草稿和精简轮次索引。压缩后存在信息缺口或具体结论有疑问时，再定点读取相关原文。
- 尊重用户审核和修改草稿的能力，先形成可审核的主题、结论和状态，保留用户编辑，依反馈迭代。具体遵循 [讨论树维护约定](references/map-maintenance.md)。
- 在支持原生 HTML 折叠的 Markdown 预览中阅读记录。仅追加日志时 `pN` 锚点保持稳定。
- 支持 Linux/macOS 本地日志，后台 systemd 服务限 Linux。远程或云端聊天需要先取得本地 rollout 文件。

## 参考

- [references/codex.md](references/codex.md) 说明 Codex 日志字段、导出范围和验证方法。
- [references/subscriptions.md](references/subscriptions.md) 说明查询字段、状态判断和退订语义。
