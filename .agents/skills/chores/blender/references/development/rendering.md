- agent name: gpt-6-astra
- harness: codex
- session: 01a1cb71
- time: 2026-11-12 06:39 (Asia/Shanghai)

# 渲染实验模块

先遵循 [使用前约定](../../SKILL.md)，通过 `run.py` 调用 `render.py`。
参数：`--output` 新 PNG 路径，`--scene`、`--camera`、`--frame` 可选，`--width`、`--height`、`--samples` 控制预览。
默认保留工程的渲染引擎；`--engine` 可显式选 CYCLES 或 BLENDER_EEVEE。Cycles 使用 CPU，采样数只用于 Cycles。
默认尺寸为 256×256，Cycles 采样数为 8；正式输出需根据效果和时间成本另定。
写入 PNG 与同名 `.render.json`；已有输出会阻止执行，场景设置只修改本次进程，原工程保持原样。
具体调用见 [渲染例子](../examples/render.md)。该入口只处理单帧，动画和 GPU 配置留待独立任务验证。
