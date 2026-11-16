# TeX 模板契约

## 选择优先级

1. 用户明确指定的模板或 sandbox。
2. 官方 TeX 的 class/style（用户未指定另一模板时）。
3. `assets/templates/single-column-bilingual/` 内置模板。

用户说“类似某 sandbox”时必须读取并复用真实模板文件，不得凭记忆近似。

## 硬约束

开始写正文前记录并锁定：document class/options、栏数、纸张、基础字号、Latin/CJK/数学字体、geometry、段落、标题、caption 和超链接样式。未经用户明确要求，不得使用双栏。

双语版本原则上保持相同纸张、页边距、基础字号和视觉层级。内置模板是 11 pt、Letter、1 inch 页边距、单栏，并带 `\bm`、`\eqref` 和文献条目跳转。

## 验收

用 `pdfinfo`、`pdffonts`、`pdftohtml -xml` 检查物理参数和字体，并查看标题页、首个正文页、公式密集页、图表页和参考文献页。若用户指定模板，至少把前两页并排查看。
