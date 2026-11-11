# Codex App 本地会话适配

实现由 `scripts/codex.py` 适配原始日志，其余流程与 AGY 共用；代码维护见 [模块职责](architecture.md)。

## 定位来源

`--current --harness codex` 从 `CODEX_THREAD_ID` 读取聊天 ID。自动查找覆盖 `$CODEX_HOME/sessions/` 的日期子目录和 `$CODEX_HOME/archived_sessions/`，默认根目录为 `~/.codex`。通过文件内 `session_meta.payload.id` 核验聊天身份，避免将 session tree 的根 ID 当成当前 thread ID。

完整 ID 和至少 8 位的唯一前缀均可使用。多个候选会报错，通过 `--source` 指定准确文件。`.source.json` 保存来源 harness、完整聊天 ID 和绝对路径。日志从活动目录移动至归档目录后，下次同步会重新定位。

本工具读取本机 JSONL 文件。云端聊天、只有数据库分页记录而没有 rollout 的聊天，需要另行导出日志。导出范围取决于文件实际保留的历史，fork 只导出其本地日志中存在的记录。

## 字段与渲染

| 日志记录 | 处理 |
| --- | --- |
| `response_item` 的 user message | 作为轮次起点，排除独立的 AGENTS.md、environment_context 和 open-page 上下文块 |
| assistant message | `phase` 或 `channel` 区分过程消息与最终回复 |
| reasoning 的 `summary` | 渲染为 `Reasoning summary` 折叠块 |
| reasoning 原始内容、加密内容、assistant analysis | 不导出 |
| function/custom tool call 与 output | 按 `call_id` 配对，支持输出交错和暂未完成的调用 |
| `item_completed` | UI 镜像记录，不重复加入 Responses 层的消息和调用 |
| `task_started`、`task_complete`、`turn_aborted` | 标记轮次完成状态，优先使用真实 `duration_ms` |
| 旧版 user_message、agent_message 事件 | 对应角色没有 Responses 消息时作为回退 |
| `compacted` | 标记上下文压缩发生的位置 |
| 图像输入 | 内嵌 data URI 解码为独立附件并显示图片；可用本地图片复制到归档；不下载远程图片，其余图像保留占位 |

Code Mode 外层调用的源码和返回结果进入工具折叠块，内层执行事件不会再重复计数。公开摘要缺失时省略推理块，不能从空摘要推断没有推理。手工讨论树需要结合用户目标整理，脚本只负责初始化模板。

## 持续同步

轮询缓存来源路径，只在首次加载或日志移动时重新搜索目录。写入使用文件锁和原子替换，支持手工同步与后台进程同时运行。新建 `map.md` 和缺失的 `memory/` 模板使用独占创建，已有讨论树、记忆文件和附件原样保留。后台同步只负责文件初始化与保留；草稿由 agent 整理，正式记忆由人类审核决定，见 [memory.md](memory.md)。

`assets.py` 负责将导出内容中的 data URI、MCP 图像/音频块解码存入 `assets/media/<sha256>.<扩展名>`，同内容复用同一路径。工具调用及结果合计超过 16 KiB，或任一行超过 4096 字符时，已分离附件的完整记录存为 `assets/tool-output/<sha256>.txt`；正文显示最多 2000 字符、30 行预览。用户及助手正文通过相对路径显示图片；助手 Markdown 图片引用的可用本地文件会复制到归档，代码示例中的路径不改写。工具记录只展示图片链接，避免一次加载所有过程截图。无法解码的文本保持原样，源日志始终不修改。用户消息中明确的 Codex 附件包装会清理，保留实际请求和图片。

正文相同（忽略署名时间）时不写入，避免仅 token 用量等未导出事件更新导致编辑器重新加载。同步状态时间存放于 `.sync-state.json`。目前仍全量读取、解析来源，尚未实现 JSONL 增量解析。历史附件不会自动删除；移动或备份记录时应携带整个会话目录，以保留相对链接。

日志写到一半时，只忽略尚未写完的末行。中间行损坏会使该次同步失败，保留上次完整输出。更早历史被重写或截断时，按顺序生成的 `pN` 可能改变，应复核手工链接。

文件锁依赖 Unix `fcntl`。Linux/macOS 可运行单次同步和 `--watch`，Linux 可使用 systemd 用户服务。原生 Windows 尚未适配锁和服务安装。

## 验证命令

```bash
S=.agents/skills/tmp/session-map/scripts/sync.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .agents/skills/tmp/session-map/scripts/tests -v
python3 $S --harness codex --current --output-root /absolute/task/outputs/session-preview
python3 .agents/skills/meta-skill/scripts/skill_ctl.py lint .agents/skills/tmp
```

隔离预览目录应放入当前任务的 `outputs/`。确认需要持续追踪后，使用默认输出目录订阅聊天，并运行 `--watch` 或已有用户服务。

生成文件开头的署名块来自 `get_model_name.py --header`，表示绑定的源会话。后台明确传入源 harness、会话 ID 和 Codex rollout 路径，并清除运行进程继承的模型覆盖值。模型取该源会话最后记录的可核实值，会话中途切换模型时，头部不代表每一轮都使用同一模型。模型缺失时仅该字段显示 `unknown`，已知的 harness 和会话 ID 仍保留。
