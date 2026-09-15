> 迁移前的历史 README，操作步骤以 [当前说明](../README.md) 为准。

# Slidev 学术汇报研究与模板

本轮结论：Markdown 快写与鼠标排版可以结合。用普通 Markdown 承担常规页面，用原生 `v-drag` 包裹需要微调的图，公式与说明，位置写入同页 `dragPos`。已通过鼠标操作验证移动，缩放，旋转，刷新保留及侧栏编辑写回。

本轮还复现并修复了 52.19.1 的坐标缓存问题：未经修补的原版中，拖动后再用侧栏改字可能恢复旧位置。模板通过 `postinstall` 自动应用限定版本的本地补丁；复制模板时保留 `scripts/`，不要跳过安装脚本。补丁与回归用例见研究记录。

主要编辑环境是本地 Slidev。导出的 PPTX 每页是图片，无法在 PowerPoint 中继续逐个编辑原有文字与公式。需要原生可编辑 PPTX 时，应另选以 PPTX 对象为输出的工作流，不能把 Slidev 导出当作双向转换。

## 立即体验

```bash
cd /home/wudizhe001/Documents/GitHub/filter-theory-HIT/.agents/.tmp/task/2026-09-09_slidev-academic/template
npm ci
npm run dev
```

本机已安装依赖。首次复制到新机器时运行 `npm ci`，后续通常只需 `npm run dev`。若 Chromium 下载不完整，运行 `npx playwright install chromium`。

访问 <http://localhost:3030/2>，双击正文或公式，再拖动内容块。拖拽外框角点可调整尺寸，上方圆形手柄可旋转。点击空白处退出选择。操作停止后稍等，查看 `slides.md` 对应页面的 `dragPos`，刷新页面验证位置。

鼠标移到窗口左下方，可显示导航工具栏。点击 `Show editor` 后，可以在同一浏览器中边改 Markdown 边查看排版。它会自动保存到源文件。

## 文件入口

| 文件 | 用途 |
| --- | --- |
| [template/slides.md](template/slides.md) | 9 页当前汇报：封面＋4 页数学原理＋1 页 BPF 流程图＋2 页仿真总结＋致谢 |
| [template/starter.md](template/starter.md) | 5 页最小起步模板，运行 `npm run dev:starter` 后访问 3031 端口 |
| [research/WORKFLOW.md](research/WORKFLOW.md) | 写作与排版约定，可复制片段，导出及迁移方式 |
| [research/FINDINGS.md](research/FINDINGS.md) | 原生能力，实际边界，路线选择与后续研究 |
| [template/styles/academic.css](template/styles/academic.css) | 字号，颜色，页边距与双栏样式 |
| [template/layouts/academic.vue](template/layouts/academic.vue) | 正文母版与自动页脚 |
| [template/output/academic.pdf](template/output/academic.pdf) | 9 页当前汇报的 PDF 预览 |
| [template/output/academic.pptx](template/output/academic.pptx) | 9 页图片式 PPTX，供兼容播放 |
| [validation/RESULTS.md](validation/RESULTS.md) | 实际验证记录与证据路径 |

## 新建一次汇报

复制整个 `template/` 文件夹，排除 `node_modules/`，`dist/`，`dist-starter/` 与 `output/`。保留 `package-lock.json`，布局，样式与 `public/`。将 `starter.md` 的内容复制到新目录的 `slides.md`，再执行 `npm ci` 与 `npm run dev`。

当前汇报的理论与实验依据 `.agents/.tmp/task/tex-build0906`。两张仿真图从已有 CSV 重绘，没有重新运行实验；来源与数值选择见 [内容映射](research/CONTENT_MAP.md)。最小起步模板 `starter.md` 中的一维高斯图仍为解析占位图。封面标识复用用户指定的 HITSZ 仓库素材。

资料依据：[Slidev 拖拽元素](https://sli.dev/features/draggable)，[内置编辑器](https://sli.dev/features/side-editor)，[导出说明](https://sli.dev/guide/exporting)。核查日期：2026-09-09，实测版本：52.19.1。

## HITSZ 首页与标识素材

已从 `HITSZ-final-paper-draft/ppt` 复制首页同款 [HITSZ PNG 图片](template/public/hitsz-logo-genimage-hd.png)（1831×377），以及原封面布局。独立预览入口为 [template/hitsz-cover.md](template/hitsz-cover.md)，运行 `node scripts/slidev.mjs hitsz-cover.md --port 3032`。查看 [来源与使用方式](research/hitsz-cover-source/README.md) 或 [首页截图](research/hitsz-cover-source/imported-cover-preview.png)。2026-09-10 按用户要求，主演示 `slides.md` 首页直接采用 `hitsz-new-cover`，随后首页文字已由用户自行编辑，本轮六页内容更新保留了这些编辑。首页文字现保存在 `slides.md`：标题在正文的 `#` 标题中，汇报人，导师，单位与日期位于 `::details::` 下方，均可在浏览器侧栏直接编辑。`layouts/hitsz-new-cover.vue` 只负责排版。独立起步模板仍使用带 `::details::` 插槽的 `academic-cover`。

最后一页为致谢页，显示“谢谢各位老师”和“敬请批评指正”。来源放在各页讲者备注及内容映射中，不额外占用一页。致谢文字可在 Markdown 末尾直接修改，起步模板也已包含致谢页。

## 当前六页正文与编辑方式

| 页码 | 内容 |
| --- | --- |
| 2 | 状态空间模型与贝叶斯递推 |
| 3 | 经验测度近似与自举粒子滤波 |
| 4 | BPF 流程图（独立页，复用 draw.io 原图） |
| 5 | Monge，Kantorovich 与离散耦合 |
| 6 | 熵正则化，Sinkhorn 与 ETPF 重心变换 |
| 7 | Gordon 模型，实验设置与 RMSE 对比 |
| 8 | 后验密度，计算耗时与粒子数切片 |

双栏正文使用 `research-slide`，页面标题 30 px，分块标题 20 px，正文 17 px，紧凑说明 15.5 px，表格 15 px。全部六页的标题，文字，公式，表格与图片容器均可独立拖动，位置保存到 Markdown 的 `dragPos`。需要改文字就打开左下工具栏的侧栏编辑器，或直接编辑 `template/slides.md`。图内曲线和坐标轴由绘图脚本生成，拖动时以整张图为单位。

新增同类页面可复制第二页的 frontmatter 与 `v-drag` 区块。字号统一在 `template/styles/academic.css` 末尾调整。可运行 `npm run check:editor` 验证拖动后改字的保存链路；该测试临时修改再恢复 `slides.md`，执行时避免同时人工编辑。`node scripts/check-layout.mjs` 检查当前九页边界并保存截图。

## 工具栏图标空白的修复

2026-09-11 核查：当前安装和 npm 官方 `latest` 均为 Slidev 52.19.1。工具栏按钮可点击却没有图标，是启动进程继承 `VSCODE_CWD` 后，UnoCSS 66.10.1 将其识别为 VS Code 扩展环境，从而跳过 Node 图标加载器。

`npm run dev`，构建与导出脚本现统一经过 `scripts/slidev.mjs`，只在 Slidev 进程中移除这个环境标记，再执行官方 CLI。无需修改系统环境或重装依赖。请保留此脚本，优先使用 npm scripts；自定义命令用 `node scripts/slidev.mjs ...`。修复后如旧页面仍显示空白按钮，按 `Ctrl+Shift+R` 强制刷新。

## BPF 独立流程图页

第 4 页放在粒子滤波原理之后。图像引用 `/diagrams/bpf.svg`，整图坐标保存在该页 `dragPos.bpf-flowchart`，可双击拖动和缩放。点击图旁“编辑流程图”即可在 Slidev 内拖动节点和箭头、双击改字；保存后自动写回 [原 draw.io 文件](../2026-09-10_drawio-replicas/bpf/bpf.drawio) 和项目内的预览。

内嵌编辑器保存时自动更新 SVG，保持浅色白底。整图位置仍在 Markdown 中；打印和导出隐藏编辑按钮。编辑器需联网加载，播放与导出使用本地图片。详细保存位置和复用方式见 [内嵌编辑说明](research/DRAWIO_EDITING.md)。
