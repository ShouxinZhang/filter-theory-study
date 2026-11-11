- agent name: gpt-6-astra
- harness: codex
- session: 01a1cb71
- time: 2026-11-12 06:39 (Asia/Shanghai)

# 果冻预览的调用例子

先遵循 [使用前约定](../../SKILL.md)。在仓库根目录运行，先设置本次任务输出目录，再在获得用户同意后执行：

```bash
BLENDER_SKILL=.agents/skills/chores/blender
BLENDER_RENDER_OUT=/absolute/path/to/task/outputs
python3 "$BLENDER_SKILL/scripts/development/run.py" --user-confirmed \
  --blender "$HOME/.local/bin/blender" \
  --blend "$BLENDER_SKILL/assets/examples/jelly-cube/scene.blend" \
  --script "$BLENDER_SKILL/scripts/development/render.py" \
  --work-dir "$BLENDER_RENDER_OUT/render" -- --output "$BLENDER_RENDER_OUT/preview.png" \
  --width 128 --height 128 --samples 4
```

这次只做单帧 CPU 预览；以 `run.json`、PNG 与 `.render.json` 共同确认结果。
