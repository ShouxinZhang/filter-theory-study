# HITSZ 硕士中期报告模板

这是可复用模板，不是研究报告快照。封面使用填写占位符，正文仅保留章节骨架和排版示例；不含个人信息、原报告研究结论或实验图表。

## 使用

复制整个 hitsz-midterm 目录作为新报告工作区。编辑 config/cover.tex，按 sections/ 填写正文，再运行：

```bash
bash build.sh
```

脚本可从任意目录调用，支持路径中的空格和中文。依赖 Bash、XeLaTeX、BibTeX 与模板使用的 TeX 宏包；验证工具另用 ripgrep 和 pdfinfo。默认使用 TeX Live 自带 Fandol 字体，无个人字体路径。

生成文件集中在 build/，交付副本为 output/midterm-report.pdf。不要直接修改生成的 PDF 或 BBL。整个目录须一起复制，不能只拷贝主 tex。

## 文件职责

- midterm-report.tex：精简入口与章节顺序。
- config/cover.tex：姓名、学号、导师、题目和日期。
- config/options.tex：AI 声明显示开关。
- preamble/：宏包、编号、字号、浮动与算法样式、文献分页保护。
- sections/：五个报告章节；completed_work/ 放公式、算法、图表、附录示例。
- references/examples.bib：三个真实著录示例，用于测试期刊、会议、在线预印本；新报告请换成实际引用。
- hithesisart.cls、hithesisart.cfg：原样保留的学校模板文件。
- hithesis.bst：沿用当前修订后的文献样式。
- .vscode/settings.json：打开此目录为 VS Code 工作区后，保存自动调用同一 build.sh，输出位置与命令行一致。
- docs/：使用约定、来源和迁移记录；logs/ 记录迁移验收。

## 积累的配置

- 深圳硕士中期封面、目录和五节结构，正文保持模板小四字号。
- 图题、表题和算法为五号；表格采用三线表。
- algorithm2e 横线标题、行号、块竖线；输入与输出为中文。不要再同时加载 algpseudocode。
- 公式、图表及算法按节编号。
- 常规图表使用 htbp；短篇第 3 至第 5 节允许连续排版，不再每节强制填白换页。
- 参考文献孤行保护；仅含 DOI 的正式期刊不因存在 DOI 被误标为 J/OL。
- AI 声明具备目录入口，但不预填作者使用工具的事实。

排版示例不是研究内容；示例数字、占位框和提示文字必须在提交前替换。长章自然分页，需在每次增删内容后复查，不能把模板配置理解为自动排版保证。

学校类文件与本地样式保留原文件头；来源见 docs/PROVENANCE.md。未把本模板声明为学校最新官方版本。
