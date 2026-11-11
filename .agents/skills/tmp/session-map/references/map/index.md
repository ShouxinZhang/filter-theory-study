- agent name: gpt-6-astra
- harness: codex
- session: 01a1cb71
- time: 2026-11-12 06:25 (Asia/Shanghai)

# 会话地图

帮助用户记起“当时想做什么、作了什么决定、还有什么悬着”。以人类 prompt 为核心，简洁转述目的、想法、反馈和取舍。

## 按需读取

| 本次整理对象 | 输出位置（相对 session 目录） | 细则 |
| --- | --- | --- |
| 会话时序 | `map/map.md` | [map.md](map.md) |
| 数学讨论 | `map/math/<主题>.md` | [math.md](math.md) |
| 开发任务 | `map/dev/<任务>.md` | [dev.md](dev.md) |

只读取本次涉及的模块。目录组织说明留在本模块中，session 的 `map/` 直接以 `map.md` 为入口。

## 共用约定

- 保留用户编辑，以当前上下文增量整理；信息缺失时定点查阅对应 prompt。
- 篇幅以唤起用户记忆为准。Agent 回答按解释决定或标记结果的需要概括；细节链接原文或 task 文档。
- 状态同时写水果 emoji 与具体文字：🍎 已完成／已讨论；🍊 进行中／待确认／暂缓／受阻；🫐 待展开。每次选一个实际状态。
- 引用 `prompts.md#pN` 时按文件深度计算相对路径；使用 `get_model_name.py --header` 更新署名，检查文件链接与锚点。
- 交付本次更新的地图链接。会话订阅、日志同步与正式记忆维护见 [session-map](../../SKILL.md)。
