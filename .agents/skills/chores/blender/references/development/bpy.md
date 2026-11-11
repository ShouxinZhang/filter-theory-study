- agent name: gpt-6-astra
- harness: codex
- session: 01a1cb71
- time: 2026-11-12 06:39 (Asia/Shanghai)

# bpy 脚本运行

先遵循 [使用前约定](../../SKILL.md)。`run.py` 使用后台模式、初始默认配置和 `--disable-autoexec`，显式执行传入的任务脚本；任务脚本本身仍须检查。

参数：`--blender` 可执行文件，`--blend` 可选工程，`--script` 脚本，`--work-dir` 新任务目录，`--timeout` 秒数，`--threads` 线程数。`--` 后传任务脚本参数。
每次工作目录须为新路径；日志为 `run.log`，运行结果为 `run.json`。Python 异常返回非零，超时返回 124。
`inspect_scene.py --output <json>` 输出各场景、对象类型、材质引用、相机、渲染引擎与尺寸；只读取当前载入的数据。

具体调用见 [场景检查例子](../examples/inspect-scene.md)。可执行路径、工程和输出目录按当前环境确定。
