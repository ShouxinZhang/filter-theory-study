# Schema

## `anchors.json`

顶层字段：

- `source_pdf`：源 PDF 绝对路径
- `counts`：按对象类型统计
- `anchors`：锚点列表

锚点字段：

- `kind`：`equation` / `figure` / `table` / `algorithm`
- `number`：原 PDF 中显示的编号字符串
- `label`：内部稳定主键，例如 `eq:auto-8`
- `page`：页码，从 1 开始
- `line_number`：抽取文本中的页内行号
- `confidence`：`high` / `medium`
- `text`：抽取到的对象文本或 caption

## `refs.json`

顶层字段：

- `counts`：总引用数、已解析数、未解析数
- `references`：引用列表

引用字段：

- `kind`：目标对象类型
- `number`：原文中的编号
- `target_label`：解析到的稳定标签；失败时为 `null`
- `pattern`：命中的模式，例如 `Equation 5`、`Figure 2`、`bare-parenthesized-number`
- `confidence`：`high` / `medium` / `low`
- `text`：原始行文本
- `page`、`line_number`：来源定位

## `recovered_stub.tex`

约定：

- 公式默认使用 `\tag{原编号}` 临时保留 PDF 编号。
- 图、表、算法用 `\setcounter{...}{n-1}` 方式对齐原编号。
- 内部引用统一使用 `\eqref` / `\ref`，不直接写死数字。
- 生成文件的占位内容必须能继续人工编辑，不得输出不可维护的长注释噪音。
