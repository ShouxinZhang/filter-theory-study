- agent name: gpt-6-astra
- harness: codex
- session: 01a1cb71
- time: 2026-11-12 06:39 (Asia/Shanghai)

# 检查果冻工程的调用例子

先遵循 [使用前约定](../../SKILL.md)。在仓库根目录运行，先设置本次新建的任务输出目录，再在获得用户同意后执行：

```bash
BLENDER_SKILL=.agents/skills/chores/blender
BLENDER_CHECK_OUT=/absolute/path/to/task/outputs
python3 "$BLENDER_SKILL/scripts/development/run.py" --user-confirmed \
  --blender "$HOME/.local/bin/blender" \
  --blend "$BLENDER_SKILL/assets/examples/jelly-cube/scene.blend" \
  --script "$BLENDER_SKILL/scripts/development/inspect_scene.py" \
  --work-dir "$BLENDER_CHECK_OUT/inspect" -- --output "$BLENDER_CHECK_OUT/scene.json"
```

路径仅展示这次机器上的调用形式；使用前核对本机 Blender 与任务目录。场景 JSON 的实际内容由工程决定。
