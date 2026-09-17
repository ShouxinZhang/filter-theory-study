# HITSZ 硕士毕业论文模板

基于 hitszthesis 3.2.8 的独立可复用资产，入口已设为硕士模式。保留中期模板的字体、算法、参考文献定制及可选 AI 声明；正文为填写骨架和排版示例。

## 使用

复制整个目录作为论文工作区，编辑 `config/cover.tex`、`front/abstracts.tex` 和 `body/`，运行：

```bash
bash build.sh
```

需要 Bash、XeLaTeX、BibTeX，以及类文件所用 TeX 宏包和 TeX Gyre、Fandol 字体。脚本支持从任意工作目录调用及中文、空格路径。编译缓存位于 `build/`，PDF 位于 `output/main.pdf`。打开本目录作为 VS Code 工作区时，LaTeX Workshop 使用同一脚本。

## 文件职责

- `main.tex`：硕士入口，按前置部分、正文、结论、AI 声明、参考文献、附录、成果、授权、致谢、简历组织。
- `config/cover.tex`：中英文题目、作者、导师、学科、学位类型、分类号与日期；当前为学术型工学硕士示例，按实际学位修改。英文 `edate` 对应英文封面的答辩日期。
- `front/abstracts.tex`：中英文摘要；`body/`：正文，新增章后在入口添加 `\input`。
- `back/`：结论等后置内容；“人工智能使用声明”使用独立无编号章并进入目录，位于结论之后、参考文献之前。
- `config/options.tex`：默认显示 AI 声明；改为 `\IncludeAIStatementfalse` 可关闭；声明正文参照 ICLR 2027 范本译写，使用第一人称及待填占位符，须按事实填写任务与核查方式。
- `preamble/fonts.tex`：Fandol 中文由入口启用，保留 TeX Gyre Termes X 正文、Heros 无衬线、Cursor 等宽字体和 Latin Modern 求和符号；数学使用 newtxmath。
- `preamble/algorithms.tex`：中期算法样式，中文输入输出、五号、横线、行号、块竖线、隐藏分号；已改为按章编号。不要重复加载 algorithm2e 或 algpseudocode。
- `preamble/bibliography.tex`：参考文献孤行保护与条目间距补丁。
- `hithesis.bst`：实际启用的中期定制文献样式，英文姓名统一大写（含姓氏前缀及后缀），保留半角标点、会议和 DOI 规则；`hitszthesis.bst` 为导入模板原版，保留供对照。
- `references/examples.bib`：三个著录测试条目，写作时替换为实际引用。
- `hitszthesis.cls`、`hitszthesis.cfg`：原样保留；页边距、章节、题注、页眉页脚采用该学位论文类的设置。

## 使用边界

原导入目录是本硕博通用模板；本资产已切换 `type=master` 及硕博书序。所有姓名、题目、正文和成果均为填写提示；授权文字沿用类文件，签字栏为空。示例值与占位文字须在提交前替换。

AI 声明的位置和学术型/专业型字段应按实际提交要求填写。本资产基于本地提供的 2023 年版本，不声明为学校最新官方模板。保留源文件版权和 LPPL 许可，见 `License` 与 `docs/PROVENANCE.md`。

构建已检查未定义引用、内容溢出、缺字和编译错误。修改长正文后仍需检查分页与图表位置；Fandol 的 CJK Script 元数据提示不等于缺字，当前样例已完成视觉检查。
