---
name: get-model-name
description: 从当前 AI 编程会话记录读取模型名称，无法核实时返回 unknown。用于 Codex、GitHub Copilot CLI、Claude Code、OpenCode 或 Grok 生成文档、日志、审计记录和署名信息时填写精确 model slug。
---

# 获取工作模型名称

运行：

```bash
python3 .agents/skills/get-model-name/scripts/get_model_name.py
```

只使用当前会话证据。输出为精确 model slug；无法确认或运行时使用 `auto` 时输出 `unknown`，不得猜测。

自动识别失败时指定框架：

```bash
python3 .agents/skills/get-model-name/scripts/get_model_name.py --framework codex
```

可选值：`codex`、`github-copilot`（CLI）、`github-copilot-vscode`、`claude-code`、`opencode`、`grok`。

VS Code Copilot Chat（agent 模式）不导出会话 ID 环境变量；若系统提示提供了 `VSCODE_TARGET_SESSION_LOG`，须显式传入：

```bash
python3 .agents/skills/get-model-name/scripts/get_model_name.py --session-log "<VSCODE_TARGET_SESSION_LOG>"
```

脚本据此读取 `workspaceStorage/<ws>/chatSessions/<会话 ID>.jsonl`，优先取最后一个请求的 `resolvedModel`，请求未完成时取所选模型 `metadata.id`；`auto` 输出 `unknown`。跨框架集成可显式提供 `AI_MODEL_NAME`，调用方须保证它是本次调用已解析的模型标识；该值属于调用方声明，并非脚本独立核验结果。

必须提供对应会话 ID（`CODEX_THREAD_ID`、`COPILOT_SESSION_ID`、`CLAUDE_CODE_SESSION_ID`/`CLAUDE_SESSION_ID`、`OPENCODE_SESSION_ID`、`GROK_SESSION_ID`，或 VS Code 的 `VSCODE_TARGET_SESSION_LOG`/`--session-log`）。指定框架不能替代会话 ID，不扫描其他会话，不使用配置默认模型兜底。

日志结果只代表该会话最后记录的模型，不能证明尚未落盘的本次请求实际后端；无法确认时保留 `unknown`。不同工具版本可能改变日志或数据库结构，不支持的结构返回 `unknown`。
