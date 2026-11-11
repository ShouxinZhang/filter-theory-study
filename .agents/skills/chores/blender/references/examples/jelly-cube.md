- agent name: gpt-6-astra
- harness: codex
- session: 01a1cb71
- time: 2026-11-12 06:39 (Asia/Shanghai)

# 果冻立方体 · 具体实验

先遵循 [使用前约定](../../SKILL.md)。用户喜欢粉色果冻立方体，明确要求内部立方核心与半透明叠层；第二版由 agent 试作，效果待用户判断。

- [已有工程](../../assets/examples/jelly-cube/scene.blend)
- [内核近景](../../assets/examples/jelly-cube/close-up.png) · [叠层阵列](../../assets/examples/jelly-cube/layers.png)
- [生成脚本](../../assets/examples/jelly-cube/create_jelly.py)：由 Blender 执行，需 `--user-confirmed --output-dir <新目录>`。

脚本会建立自己的场景并渲染后保存工程；通过启动器的默认空白场景运行。颜色、内核尺寸、光照、叠层数量都属于本例的实验选择。
来源：本 session 的粉色立方体任务。收纳时增加了输出目录、确认参数，以及 `--resolution-percent`、`--samples` 预览参数，完整重新生成的验证状态见 [记录](../validation.md)。
