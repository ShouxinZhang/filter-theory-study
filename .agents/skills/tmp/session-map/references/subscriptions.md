# 订阅查询与管理

## 命令

```bash
S=.agents/skills/tmp/session-map/scripts/sync.py
python3 $S list --json
python3 $S list --all --harness codex --json
python3 $S show 01a1a583 --json
python3 $S subscribe --harness codex --current --json
python3 $S unsubscribe 01a1a583 --json
```

`list` 默认返回已登记订阅，`--all` 同时包含退订后保留的文档。`show` 和 `unsubscribe` 支持完整 ID、唯一前缀及 `--current`。`subscribe` 还支持 `--source` 指定日志。

全部子命令支持 `--output-root` 隔离输出目录。`--json` 成功时 stdout 只输出一个 JSON 对象。业务错误输出含 `error` 的 JSON 并返回非零退出码，参数语法错误由 argparse 写入 stderr。

查询读取订阅状态文件，并检查进程和源文件状态。部分订阅损坏时，列表仍返回其余结果，损坏项单独标记错误。

## JSON 字段

`list` 返回 `watcher` 和 `subscriptions` 数组，其余命令返回 `watcher` 和单个 `subscription`。

| 字段 | 含义 |
| --- | --- |
| `id`、`harness` | 完整会话 ID 和来源 |
| `name`、`name_source` | 展示名称，默认来自首次同步时的首条提问，`first_prompt` 明示来源；缺失时回退 ID |
| `subscribed` | 已登记且未退订 |
| `watching` | 已订阅且该输出根目录的 watcher 心跳正常 |
| `sync_status` | 当前源日志与最近成功输出的关系 |
| `source_path`、`source_modified_at` | 日志路径和最后修改时间 |
| `last_synced_at`、`last_attempt_at` | 最近成功同步时间和最近尝试时间，含时区 |
| `turn_count` | 最近成功同步识别出的提问轮数 |
| `error` | 最近同步失败或状态读取错误 |
| `map_path`、`prompts_path` | 新版 `map/map.md` 与 `prompts.md` 的绝对路径；旧订阅下次同步时迁移地图 |
| `memory_path`、`memory_drafts_path`、`memory_references_path` | 本 session 正式记忆、待审核草稿和附件目录的绝对路径，供调用方按需访问 |

名称是可追溯的本地展示标签，不保证与 App 侧栏当前标题一致。

## 状态判断

`watcher.status` 分为 `running`、`stale`、`stopped`、`unknown`。通过 `.watcher.json` 中的 PID 和心跳判断，旧版进程尚未写入心跳时为 `unknown`。`stale` 表示进程存在但心跳过期，可能正在处理较慢的同步，应同时查看时间和错误。前台 `--watch` 与 systemd 服务使用相同机制。

`sync_status` 分为以下状态。

- `up_to_date` 表示源路径、修改时间和大小与成功同步快照一致，末行也完整。
- `pending` 表示源发生变化或存在尚未写完的末行。
- `source_missing` 表示来源路径当前不存在，watcher 下次尝试会重新定位已移动的日志。
- `output_missing` 表示机械输出被移除，需要重新同步。
- `error` 表示最近同步或状态读取失败。
- `unknown` 表示缺少新格式状态，常见于尚未完成首次迁移的旧订阅。

三个维度独立。例如，已退订的旧文档可以仍然与源一致；已订阅但监听进程停止的会话也可以暂时处于 `up_to_date`。

## 文件与并发

`.source.json` 绑定来源，`.sync-state.json` 保存成功快照和错误，`.unsubscribed` 表示暂停订阅。退订在同一个会话写锁下创建标记，等待正在进行的同步结束，后续 watcher 和 `--all` 跳过该会话。重新订阅成功同步后移除标记，已有 `map/map.md` 原样保留，旧版按迁移规则备份。

无需删除归档文档来退订。手工删除整个会话目录仍会停止追踪。更新脚本后需要重启已运行的 watcher，使其识别退订标记和心跳协议。
