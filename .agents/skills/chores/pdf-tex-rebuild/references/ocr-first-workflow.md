# PDF-only 直接视觉 OCR

## 页面准备

```bash
pdfinfo <paper.pdf>
mkdir -p <case_dir>/page-renders
pdftoppm -png -r 180 <paper.pdf> <case_dir>/page-renders/page
```

小字号、公式密集页使用 220--300 dpi；需要分区时使用 ImageMagick 裁剪，不为裁剪额外引入 Python。

## 页面台账

建立 `page-ledger.md`，逐页记录标题/段落、公式、图表、脚注/文献、转录状态和视觉核对状态。两栏阅读顺序、跨页段落和跨页 caption 必须显式记录。

## 直接转录

- 用视觉工具按原始细节查看页面，由模型直接写 TeX。
- 公式按图人工重录，并立即设置稳定 `label`。
- 表格按视觉结构重建，不用 OCR 空格猜列。
- `pdftotext` 只用来发现可能遗漏或核对拼写；与页面冲突时以页面为准。
- 不默认启动 Python OCR/版面解析。确有重复批处理价值时，其输出也只能作为草稿，所有受影响页面必须重新视觉核对。

## 每批闭环

每完成少量页面就编译并渲染，对照原页检查文字覆盖、阅读顺序、公式符号/编号、图表、脚注、引用、字体、裁切与空白。所有台账项勾选后才算完成。
