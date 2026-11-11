- agent name: gpt-6-astra
- harness: codex
- session: 01a1cb71
- time: 2026-11-12 05:34 (Asia/Shanghai)

# 会话时序

输出：`.agents/.tmp/session/<id>/map/map.md`，作为具体 session 的时间线与主题入口。

## 整理方式

- 按用户发言的时间或轮次，记录当时想做的事、关键决定与转向；相邻且连续的讨论可合并一行。
- 每行简述人的意图，附原文轮次、必要的当前状态及对应 math/ 或 dev/ 主题链接。
- 主题细节由对应文件承接；时序保留能帮助用户回想讨论如何推进的信息。
- 日期和时间取已知的消息记录；仅知道轮次时按轮次排列。

实际记录将轮次链接至 `../prompts.md#pN`，主题链接至 `math/<主题>.md` 或 `dev/<任务>.md`。

需要对照实际写法时，阅读 [具体例子](examples/map.md)。
