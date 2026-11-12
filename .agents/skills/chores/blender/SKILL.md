---
name: blender
description: Blender 实验技能，涵盖运维、bpy 开发、果冻与黑金校徽案例。用户尚无 Blender 经验、不具备审核能力；其他 agent 参考执行前必须询问用户，并谨慎核验适用性。
---

# Blender · 实验版

**用户声明：用户尚无 Blender 经验，暂不具备审核本技能的能力。这是 agent 自行编写和整理的实验产品，不能视为经过用户专业审核的可靠方案。**

## 使用前

1. 其他 agent 参考本技能执行任何操作前，必须先询问用户；说明计划做什么、影响哪些文件或环境、预计产物与已知不确定性。
2. 用户同意本次范围后再执行；用户同意代表授权，不代表技术或视觉正确性已获审核。Agent 仍须谨慎核验本机版本、输入和实际结果。
3. 脚本的 `--user-confirmed` 只记录已得到本次授权。先问用户，再传入该标志，不能用标志代替询问。
4. 先在任务目录验证；把可复现结果、失败和未验证部分记录到 task 文档，保留用户工程。

## 按需读取

| 任务 | 模块 |
| --- | --- |
| 安装、升级、配置与环境检查 | [运维](references/operations/index.md) |
| bpy、材质、渲染、MCP | [开发技术](references/development/index.md) |
| 参考粉色内核与半透明叠层 | [果冻具体案例](references/examples/jelly-cube.md) |
| 参考独立黑金校徽、金属浮雕与本地 3D 页面 | [HIT 黑金校徽案例](references/examples/hit-black-gold.md) |
| 将案例发展成可复用模板 | [模板状态](references/templates/index.md) |

## 代码与资产

- `scripts/operations/`：系统 Python 的环境检查和本地安装包安装工具。
- `scripts/development/run.py`：从系统 Python 启动 Blender，保存日志和退出状态。
- `scripts/development/inspect_scene.py`、`render.py`：由 Blender 内置 Python 执行。
- `assets/examples/jelly-cube/`：已有工程、两张预览与案例专用生成脚本。
- `assets/examples/hit-black-gold/`：黑金校徽工程、矢量源、两张预览、复现脚本与离线 3D 页面。
- 初次编写时的验证范围见 [实验验证记录](references/validation.md)；视觉效果和可迁移性仍需实际验证。
