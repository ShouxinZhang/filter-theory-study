- agent name: gpt-6-astra
- harness: codex
- session: 01a1cb71
- time: 2026-11-12 06:39 (Asia/Shanghai)

# 材质实验说明

先遵循 [使用前约定](../../SKILL.md)。节点、插槽名称和参数范围需要在实际 Blender 版本核对。
使用 bpy 操作材质时，先读场景与材质节点，再进行最小修改，用低分辨率预览判断结果。
目前积累来自 [果冻案例](../examples/jelly-cube.md)：外层、内核与下层分别建模，用不同材质表达透光和颜色。
这些参数是 agent 对参考图的实验选择，尚未获得用户视觉验收；颜色、透射与内核比例保存在案例脚本中。
