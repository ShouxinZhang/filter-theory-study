- agent name: gpt-6-astra
- harness: codex
- session: 01a1a583
- time: 2026-11-08 13:42 (Asia/Shanghai)

# 模块职责与调用流程

运行代码和测试都在 `scripts/`，测试集中放在 `scripts/tests/`。面向使用者的命令统一由 `sync.py` 提供；不直接执行内部模块。

## 四块职责

| 模块块 | 文件 | 负责内容 |
| --- | --- | --- |
| 日志适配 | `codex.py`、`antigravity.py` | 识别各自日志、取得会话 ID、发现候选文件、解析为共同轮次；工具配对和格式差异在这里消化 |
| 来源管理 | `sources.py`、`models.py` | 选择适配器、读取 JSONL 快照、验证身份、定位绑定来源、获取署名；共享 Source 与时区定义 |
| 内容渲染 | `render.py`、`assets.py` | 轮次索引、折叠块、Markdown、附件及链接；渲染器接收已解析轮次，不搜索或读取日志 |
| 订阅运行 | `runtime.py`、`sync.py` | 运行层管理状态、锁、原子写入、监听和 systemd；CLI 层处理参数与输出 |

依赖方向：`sync → runtime → sources / render / assets`；`sources → 两种适配器`；`models` 不依赖其他业务模块。渲染器不反向调用运行层。

## 一次同步

1. CLI 解析命令，运行层确定归档位置。
2. 来源层通过适配器定位并核验日志，运行层取得该会话文件锁。
3. 读取完整 JSONL 快照，选中适配器生成轮次；尚未写完的末行暂缓处理。
4. 渲染器和附件模块生成正文；运行层比较并原子写入，更新同步状态。
5. 仅当 `map.md` 不存在时建立模板。已有讨论树始终保留。

`runtime.render()` 是读取、解析与渲染的组合入口；`render.render()` 只接受轮次数据和明确署名。按需读取状态的 `list/show` 不走全量解析。

## 适配器接口

两种适配器都提供：

- `matches(records)`：是否识别这种原始日志。
- `session_id(records, path)`：取得日志中或目录中的会话 ID，由来源层统一验证。
- `find_paths(root, prefix)`：产生候选本地日志路径。
- `parse_turns(records, assets=None)`：产生标准轮次，来源层统一收集为列表。

轮次以 `user` 和 `steps` 为核心，用户包含 `content`、`created_at`，步骤保留 `type`、`content`、`created_at` 等字段。可选的状态、结束时间、持续时间由适配器提供。为兼容已有输出，步骤类型继续使用 `PLANNER_RESPONSE` 等既有名称。

工具调用统一放在步骤的 `tool_calls`，每条调用自身携带配好的 `result` 或 `pending`。Codex 按 `call_id` 配对；AGY 在适配器内配对紧随回复的 `GENERIC` 记录。共同渲染器不再推测 AGY 原始日志的邻接关系。

Codex 的公开推理摘要筛选和事件去重仍由 `codex.py` 负责。图片解码、文件链接转换和大工具输出折叠属于 `assets.py`，两种适配器共用。

## 改动定位和验证

- 某个 harness 少了消息或工具配错：检查对应适配器。
- 找不到日志、身份或署名错误：检查 `sources.py`。
- 内容正常但 Markdown、链接、图片异常：检查 `render.py` / `assets.py`。
- 订阅状态、并发写入或监听异常：检查 `runtime.py`；参数行为检查 `sync.py`。

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .agents/skills/tmp/session-map/scripts/tests -v
```

回归覆盖两种日志、媒体和链接、订阅/退订、损坏与未完成日志、真实 watch 子进程以及 systemd 入口。涉及模块移动时还应比较固定输入的生成结果；运行中的服务不会自动重载 Python 模块，验证后执行 `systemctl --user restart session-map-sync.service`。
