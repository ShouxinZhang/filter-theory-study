---
name: session-map
description: 为 Antigravity 与 Codex App/CLI 的本地长会话维护会话时序与主题 map/、折叠记录 prompts.md 和 session 专属 memory。用于恢复上下文、整理记忆草稿、人类审核正式记忆，以及订阅查询、订阅管理和后台热同步。
---

# session-map

在 `.agents/.tmp/session/<id>/` 下维护用户的会话地图、记录及附件。
- `map/` 以人类 prompt 为核心维护时序、数学思路与开发任务，内容整理交给 [map 子技能](../map/SKILL.md)。
- `prompts.md` 由本地日志机械生成，通过 `<details>` 折叠过程和工具输出，最终回复在外层显示。
- `memory/` 仅属于该 session：后台脚本负责建立缺失的目录和空白模板、保留已有文件；记忆草稿由 agent 整理，正式记忆由人类审核决定。AI 草稿不具备规则效力。
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

## 工作流模块

### 会话地图维护

- 用户要求整理时序、数学讨论或任务进度时，读取 [map 子技能](../map/SKILL.md)，更新 `map/map.md` 与有关主题。
- 现有同步脚本仍在 session 根目录初始化旧 `map.md`，`show/list` 的 `map_path` 也指向旧文件；新版内容由 agent 写入 `map/`。读取新版地图时使用 `map/map.md`。

### 记录生成

- 两种 harness 经各自适配器转换为统一轮次，再共用 Markdown 渲染和附件处理。
- 首次同步保存 `.source.json`，后续沿用来源；署名由绑定源会话生成，不使用后台进程所属聊天的身份。
- 在支持 HTML 折叠的 Markdown 预览中阅读。日志仅追加时 `pN` 稳定；本工具读取本地日志，云端聊天需先取得日志文件。

### Session 记忆

- 继续或恢复本 session 时读取 `memory/memory.md`；草稿仅在整理或审阅时读取，引用附件按任务需要读取，不跨 session 自动共享。
- AI 可主动 CRUD `memory/agent-memory-drafts.md`；每条草稿和正式记忆至多两行，长内容放 `memory/references/`。
- 用户要求“总结 memory”时先整理并对齐，以人类明确确认的内容和范围更新正式记忆，并保留人类直接修订。细则见 [memory.md](references/memory.md)。

### 订阅与后台

- 查询订阅先用 `list --json` 或 `show ID --json`，分别查看 `subscribed`、`watching`、`sync_status`，据此判断订阅、监听及同步状态。
- 订阅/退订使用对应命令；退订保留文档。旧式 `sync.py ID` 和 `--current` 仍等价于订阅并同步。无法唯一识别当前聊天时，指定 harness 和 ID。
- `--watch` 每秒检查日志变化；正文不变时不重写 `prompts.md`，附件不变时不重写。删除归档目录会停止追踪；脚本升级后重启已有服务。
- 单次同步和 watch 支持 Linux/macOS；systemd 用户服务限 Linux。详情见 [订阅管理](references/subscriptions.md)。

### 代码维护

- 运行代码和测试统一放在 `scripts/`，测试位于 `scripts/tests/`。
- 修改解析、渲染或同步逻辑前，按 [模块职责与调用流程](references/architecture.md) 找到负责模块。
- 保留 `sync.py` 命令入口、已有状态文件及 `map.md`；运行回归测试，脚本升级后再重启监听服务。

## 参考

- [references/codex.md](references/codex.md) 说明 Codex 日志字段、导出范围和验证方法。
- [references/subscriptions.md](references/subscriptions.md) 说明查询字段、状态判断和退订语义。
