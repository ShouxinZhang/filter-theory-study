- agent name: gpt-6-astra
- harness: codex
- session: 01a1cb71
- time: 2026-11-12 04:11 (Asia/Shanghai)

# 模块职责与调用流程

运行代码和测试都在 `scripts/`，测试集中放在 `scripts/tests/`。使用者通过 `sync.py` 执行命令，内部模块由该入口调用。

## 四块职责

| 模块块 | 文件 | 负责内容 |
| --- | --- | --- |
| 日志适配 | `codex.py`、`antigravity.py` | 识别各自日志、取得会话 ID、发现候选文件、解析为共同轮次；工具配对和格式差异在这里消化 |
| 来源管理 | `sources.py`、`models.py` | 选择适配器、读取 JSONL 快照、验证身份、定位绑定来源、获取署名；共享 Source 与时区定义 |
| 内容渲染 | `render.py`、`assets.py`、`memory.py`、`map_layout.py` | 渲染器将已解析轮次生成索引与折叠记录；附件模块处理媒体和链接；memory.py 建立缺失的记忆模板；map_layout.py 负责地图路径与迁移 |
| 订阅运行 | `runtime.py`、`sync.py` | 运行层管理状态、锁、原子写入、监听和 systemd；CLI 层处理参数与输出 |

依赖方向：`sync → runtime → sources / render / assets / memory / map_layout`；`sources → 两种适配器`。`models` 提供各模块共用的数据结构与时间处理函数。

## 一次同步

1. CLI 解析命令，运行层确定归档位置。
2. 来源层通过适配器定位并核验日志，运行层取得该会话文件锁。
3. 读取完整 JSONL 快照，选中适配器生成轮次；尚未写完的末行暂缓处理。
4. 渲染器和附件模块生成正文；运行层比较并原子写入，更新同步状态。
5. 通过 `map_layout.py` 初始化 `map/map.md` 并迁移旧地图，随后初始化缺失的 `memory/` 文档；已有新版地图和记忆（包括空文件）原样保留。

旧地图先按内容哈希保存原始字节至 `assets/legacy-map/`。新版已存在时保留新版；只有旧版时迁入并调整 Markdown 相对链接。目标文件以独占方式发布，备份成功后才移除根目录旧入口。备份保留原文，链接仍以旧 session 根目录为基准。

`runtime.render()` 组织日志读取、解析与渲染；`render.render()` 根据轮次数据和署名生成文档。`list/show` 读取订阅状态文件，并检查源文件与监听进程状态。

## 适配器接口

两种适配器都提供：

- `matches(records)`：是否识别这种原始日志。
- `session_id(records, path)`：取得日志中或目录中的会话 ID，由来源层统一验证。
- `find_paths(root, prefix)`：产生候选本地日志路径。
- `parse_turns(records, assets=None)`：产生标准轮次，来源层统一收集为列表。

轮次以 `user` 和 `steps` 为核心，用户包含 `content`、`created_at`，步骤保留 `type`、`content`、`created_at` 等字段。可选的状态、结束时间、持续时间由适配器提供。为兼容已有输出，步骤类型继续使用 `PLANNER_RESPONSE` 等既有名称。

工具调用统一放在步骤的 `tool_calls`，每条调用自身携带配好的 `result` 或 `pending`。Codex 按 `call_id` 配对；AGY 在适配器内配对紧随回复的 `GENERIC` 记录。共同渲染器使用适配器完成配对的数据。

Codex 的公开推理摘要筛选和事件去重仍由 `codex.py` 负责。图片解码、文件链接转换和大工具输出折叠属于 `assets.py`，两种适配器共用。

## 改动定位和验证

- 某个 harness 少了消息或工具配错：检查对应适配器。
- 找不到日志、身份或署名错误：检查 `sources.py`。
- 内容正常但 Markdown、链接、图片异常：检查 `render.py` / `assets.py`。
- 地图路径、初始化或迁移异常：检查 `map_layout.py`；`map_path()` 同时供初始化和查询使用。
- 记忆模板初始化异常：检查 `memory.py` 和 `references/templates/`；审核、两行条目和继承边界由 [memory.md](memory.md) 规定。
- 订阅状态、并发写入或监听异常：检查 `runtime.py`；参数行为检查 `sync.py`。

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .agents/skills/tmp/session-map/scripts/tests -v
```

回归覆盖两种日志、媒体和链接、订阅/退订、损坏与未完成日志、真实 watch 子进程以及 systemd 入口。涉及模块移动时还应比较固定输入的生成结果；验证后执行 `systemctl --user restart session-map-sync.service`，使服务加载更新后的 Python 模块。
