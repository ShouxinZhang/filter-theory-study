# 这份汇报

编辑 `slides.md`，把自己的图片放进 `public/`。在本目录执行 `./start.sh`（默认 3030），或 `./start.sh 3031`。从工作区根目录也可执行 `npm run dev -- <本目录名>`。默认字体与布局来自共享 HITSZ 主题。

封面日期在 `::details::` 下方。第二页展示小字号、双栏和独立拖拽，最后一页是致谢。示例高斯图仅为占位，正式汇报前替换。

如需可编辑流程图，将配对的 `.drawio` 和白底 `.svg` 放进 `public/diagrams/`，在 `drawio.config.mjs` 启用对应图 ID，然后在 Markdown 中写：

```html
<DrawioDiagram id="flow" src="/diagrams/flow.svg" alt="流程图" />
```

修改映射后重启服务。图内文字通过 Draw.io 编辑器修改；普通正文与整图拖拽位置在 Markdown 中保存。

底部工具栏的“排序”可拖动缩略图调整页序并自动保存；首张封面固定在首位。

复制截图或图片后，可在幻灯片画面或 Markdown 编辑框按 Ctrl+V 插入图片。素材保存在本 talk 的 `public/images/`；双击图片可拖动与缩放。
