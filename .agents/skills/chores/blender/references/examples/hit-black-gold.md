- agent name: gpt-6-astra
- harness: codex
- session: 01a1cb71
- time: 2026-11-12 07:56 (Asia/Shanghai)

# HIT 黑金校徽 · 具体实验

先遵循 [使用前约定](../../SKILL.md)。用户选择独立金属校徽，偏好黑金配色，并要求保存此案例；技术正确性仍属实验验证范围。

## 素材

- [Blender 工程](../../assets/examples/hit-black-gold/scene.blend) · [斜视预览](../../assets/examples/hit-black-gold/preview.png) · [正面图](../../assets/examples/hit-black-gold/front.png)
- [校徽矢量源](../../assets/examples/hit-black-gold/source/emblem.svg)：中文版“哈工大”，275 个路径保持可编辑。
- [本地 3D 页面](../../assets/examples/hit-black-gold/web/index.html) · [启动脚本](../../assets/examples/hit-black-gold/web/start.sh) · [GLB 模型](../../assets/examples/hit-black-gold/web/assets/hit-black-gold.glb)

## 复现

[生成脚本](../../assets/examples/hit-black-gold/scripts/create_scene.py) 由 Blender 执行，接受 `--user-confirmed --output-dir <新目录>`，可选 `--resolution 800 --samples 48`。路径解析和几何模块在其同目录。
通过 [后台启动器](../../scripts/development/run.py) 传入上述脚本，使用新的 task 输出目录；脚本读取随附 source/emblem.svg，无需访问原 session 或下载素材。
[网页导出脚本](../../assets/examples/hit-black-gold/scripts/export_web.py) 在此工程中运行，接受 `--user-confirmed --output <新路径.glb>`，将曲线烘焙为两种材质的网格。
网页已包含模型与 Three.js 0.187.0。进入 web/ 执行 `bash start.sh`，打开终端给出的本地地址；端口占用时可用 `bash start.sh 8842`。

## 来源与验证

矢量取自 [维基百科文件页](https://zh.wikipedia.org/wiki/File:Harbin_Institute_of_Technology_logo.svg)，该页注明提取自哈工大百年标识使用手册；校徽权利归校方，页面未提供自由再许可。
本次创作部分为金属材质、分层浮雕、深色衬底与布光。原图形为中文版校徽；窗格和文字使用源路径。
已在 Blender 5.3.0 完成两视角渲染；浏览器验证加载、旋转、缩放、平移、复位、自动旋转、窄屏和失败重试。归档后的脚本另做低分辨率重建与 GLB 导出检查。
工程适用于视觉创作，衬底仍由相交部件组成；制作实体前需另行合并与检查。实时网页与 Cycles 的光照效果有所区别。
