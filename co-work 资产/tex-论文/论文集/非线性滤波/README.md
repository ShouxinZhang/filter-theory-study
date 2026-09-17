# 联合优化下的非线性滤波：神经网络与输运方法

这是由 2026 年 9 月 15 日中期报告迁移形成的硕士毕业论文工作稿。研究内容来自用户指定 PDF 对应的源码，采用 `../../模板/hitsz-master` 的排版与四项定制。此目录已包含所有编译依赖文件，可独立复制使用。

## 阅读与编译

- [毕业论文 PDF](output/main.pdf)：当前 42 页。
- [迁移记录](docs/MIGRATION.md)：来源、章节映射和待补内容。
- [验收记录](docs/VALIDATION.md)：内容完整性与编译检查。

在本目录运行 `bash build.sh`；也可从任意目录用完整路径调用该脚本。依赖 Bash、XeLaTeX、BibTeX 和模板使用的 TeX 宏包。缓存位于 `build/`，交付 PDF 为 `output/main.pdf`。VS Code 打开本目录或仓库根目录时，均通过 HITSZ build 使用同一构建流程；View LaTeX PDF 预览本论文的 `build/main.pdf`，`output/main.pdf` 是同步的交付副本。各子 TeX 已显式指向本目录的 `main.tex`，排障记录见 `docs/VSCODE-PREVIEW-FIX.md`。

## 内容组织

- `main.tex`：章序与前后置内容。
- `config/cover.tex`：保留报告的中文题目、作者、学号与学科；封面所在单位为哈尔滨工业大学（深圳），导师为严质彬教授，学位为学术型理学硕士。分类号 O1 / 51，密级公开，英文姓名与题目已按认可的草案填写；毕业日期仍待填。
- `body/chapter01.tex`：研究背景与阶段进展。
- `body/chapter02.tex` 与 `sections/completed_work/01` 至 `04`：理论基础。
- `sections/completed_work/05_algorithms.tex`：算法分析；`06_simulation.tex`：仿真实验。
- `body/chapter05.tex` 与 `sections/03` 至 `05`：原中期后续工作、困难及可行性分析。
- `sections/completed_work/07_supporting_proofs.tex`：正式附录 A，包含符号说明和证明。
- `figs/completed_work/`：原报告实际引用的五幅 PDF 图；`references/`：原始两份文献库。
- `back/ai_statement.tex`：原报告的实际 AI 使用说明，按毕业论文配置放在结论之后、参考文献之前。

摘要、最终结论、成果清单、致谢、简历在源报告中缺失，已明确标为待补。保留原文的“尚未开展”“后续拟”等阶段措辞；没有将研究计划改成已完成成果。关键词为依据正文提取的初步配置。

本目录的 `.cls/.cfg` 和文献样式保留第三方版权，见 `License`。此稿迁移的是已有内容与格式，不代表毕业论文研究已完成，也未重新核验原报告中的科学结论或引用事实。
