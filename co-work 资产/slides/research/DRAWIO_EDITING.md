# 在 Slidev 中编辑 draw.io 流程图

打开本地开发服务的第 4 页，点击图右上方的“编辑流程图”。页面内打开 draw.io：拖动节点或箭头端点，双击标签改字，使用 draw.io 的“保存”或“保存并退出”。窗口较小时，可点击上方“适应窗口”查看完整图，再用 draw.io 缩放工具放大局部。保存后立即更新当前幻灯片，无需手动导出或切换应用。

整张图的位置仍由 Markdown 的 `dragPos.bpf-flowchart` 管理。进入编辑模式不会修改这个坐标。Markdown 的图引用现在是：

```vue
<DrawioDiagram id="bpf" src="/diagrams/bpf.svg" alt="BPF 流程图" />
```

外面仍保留原 `v-drag` 容器，所以双击整图可调整在幻灯片中的位置。“编辑流程图”按钮用于进入图内编辑。

## 保存位置

每份汇报通过自己的 `drawio.config.mjs` 指定图形路径，共享插件自动读取它。当前 BPF 配置位于 `talks/filtering/drawio.config.mjs`：

```js
export default {
  bpf: {
    source: 'public/diagrams/bpf.drawio',
    preview: 'public/diagrams/bpf.svg',
  },
}
```

路径相对于本汇报目录。保存只更新本汇报的 `.drawio` 与 `.svg`；原 `2026-09-10_drawio-replicas/bpf/` 是来源档案，不再自动同步。SVG 固定浅色白底，文字、公式与连线由 Draw.io 生成。

每次成功保存前，会在本汇报的 `.drawio-history/bpf/` 留存此前的源文件与预览。文件被其他窗口修改时会拒绝覆盖。保存失败可在编辑器重试，或点击“下载当前修改”保留草稿。退出前若有未保存修改，可选择继续编辑或放弃。

新建图形时把配对的 `.drawio` 与 SVG 放到本汇报的 `public/diagrams/`，添加映射并重启服务，然后用对应的图 ID 和 SVG 地址插入组件。新建汇报默认映射为空，不会引用 BPF 或其他汇报的图形。

## 演示与导出

编辑器使用 draw.io 官方在线嵌入服务，需要联网加载。平时展示、静态构建和 PDF/PPTX 导出使用本地 SVG，无需加载编辑器。编辑按钮只出现在本地开发服务中，打印和导出中隐藏。新修改需要重新运行 `npm run export:pdf` 或 `npm run export:pptx` 才会更新已导出的文件。

使用 `npm run dev` 启动。文件写回接口只在 Vite 开发服务中存在。静态发布没有写回功能。修改路径配置后需要重启服务；所有图形路径都必须位于当前汇报内。

## 实现与验证入口

- `packages/addon-drawio/components/DrawioDiagram.vue`：预览、内嵌编辑器、保存状态和退出处理。
- `packages/addon-drawio/server/drawio.mjs`：图 ID 白名单、版本冲突检测、备份、同步写入。
- `packages/addon-drawio/vite.config.ts`：挂载开发保存接口，避免保存触发整页重载。
- `npm run check:drawio`：在独立临时目录测试正常保存、冲突、错误来源和无效数据；不触碰真实图。

嵌入层检查消息来源与窗口。服务端只接受配置的图 ID，不接收客户端文件路径；写入校验 Origin、XML/SVG 格式和请求大小。SVG 预览通过 `img` 加载，图中脚本和事件处理属性被拒绝。

参考：[draw.io Embed mode](https://www.drawio.com/docs/reference/embed-mode/)。采用 `load`、`save`、`export` 和 `status` 消息。数学图导出直接使用当前编辑画布，关闭字体嵌入，避免重新加载 XML 再导出时的阻塞。
