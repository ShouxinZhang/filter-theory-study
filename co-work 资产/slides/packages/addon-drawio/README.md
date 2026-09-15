# Draw.io Editor Addon

在幻灯片头部声明 `addons: [drawio-editor]` 即可使用 `DrawioDiagram` 组件与开发服务保存接口。无需为每份汇报复制 `vite.config.ts` 或服务端代码。

插件从当前幻灯片目录读取 `drawio.config.mjs`，文件缺省或空对象表示没有启用图形。每张图必须配置 `source` 与 `preview`，路径必须位于当前汇报内。可选 `copy` 和 `sourcePreview` 用于额外的同汇报副本。修改映射后重启服务。

保存前版本冲突检查与历史备份沿用现有实现，历史位于该汇报的 `.drawio-history/`。SVG 固定白底。编辑器需要联网，静态演示和导出使用本地预览。详细用法见工作区 `research/DRAWIO_EDITING.md`。
