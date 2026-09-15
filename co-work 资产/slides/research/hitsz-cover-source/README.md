# HITSZ 首页素材

来源：本机 `HITSZ-final-paper-draft/ppt/`，复制于 2026-09-10。

- `first-slide.md` 与 `hitsz-new-cover.vue` 保留原首页源文件。
- 当前首页使用 `hitsz-logo-genimage-hd.svg`，它是嵌入 PNG 的 SVG 容器，不是可无限放大的矢量轮廓。
- 对应 PNG 为 1831×377，白底备用版本为 365×67。保留原文件名和原始字节，没有重新绘制标识。
- 图片已放入 `../../template/public/`。`manifest.json` 记录来源与 SHA-256。
- `../../template/hitsz-cover.md` 是独立首页预览，保留原汇报标题与作者信息，运行 `npx slidev hitsz-cover.md --port 3032`。
- `source-first-page.png` 是原仓库已有 PDF 的第一页预览，不保证该 PDF 与当前源文件生成时间一致。

在当前 Markdown 中插入首页同款图：

```html
<img src="/hitsz-logo-genimage-hd.png" alt="哈尔滨工业大学（深圳）" style="width: 500px; height: auto" />
```

此处仅复用用户指定仓库素材，不额外认定素材的官方发布来源。

当前模板的封面布局已改为读取 Markdown 插槽，以便侧栏编辑文字。此目录内的源文件仍保留原仓库副本。日期入口为 `../../template/slides.md` 第一页 `::details::` 下的最后一行。
