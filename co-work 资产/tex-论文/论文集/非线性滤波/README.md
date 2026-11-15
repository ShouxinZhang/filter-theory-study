# 联合优化下的非线性滤波——神经网络与输运方法

这是由 2026 年 9 月 15 日中期报告迁移形成的硕士毕业论文工作稿。研究内容来自用户指定 PDF 对应的源码，版式已切换对齐深圳校区教务部发布的《深圳校区硕士学位论文写作范例-学术学位》（`hithesisbook` `2025/03/03 v3.1d`），并保留字体、求和符号、算法排版及英文文献作者姓名全大写定制。此目录已包含所有编译依赖文件，可独立复制使用。

## 阅读与编译

- [毕业论文 PDF](output/main.pdf)：当前 41 页。
- [迁移记录](docs/MIGRATION.md)：来源、章节映射和待补内容。
- [验收记录](docs/VALIDATION.md)：内容完整性与编译检查。

在本目录运行 `bash build.sh`；也可从任意目录用完整路径调用该脚本。依赖 Bash、XeLaTeX、BibTeX 和模板使用的 TeX 宏包。缓存位于 `build/`，交付 PDF 为 `output/main.pdf`。VS Code 打开本目录或仓库根目录时，均通过 HITSZ build 使用同一构建流程；View LaTeX PDF 预览本论文的 `build/main.pdf`，`output/main.pdf` 是同步的交付副本。各子 TeX 已显式指向本目录的 `main.tex`，排障记录见 `docs/VSCODE-PREVIEW-FIX.md`。

## 内容组织

- `main.tex`：章序与前后置内容。
- `config/cover.tex`：保留报告的中文题目、作者、学号与学科；封面所在单位为哈尔滨工业大学（深圳），导师为严质彬教授，学位为学术型理学硕士。分类号 O1 / 51，密级公开，主副标题按学校规范中文采用破折号、英文采用冒号；毕业日期仍待填。
- `body/chapter01.tex`：研究背景与阶段进展。
- `body/chapter02.tex` 与 `sections/completed_work/01` 至 `04`：理论基础。
- `sections/completed_work/05_algorithms.tex`：算法分析；`06_simulation.tex`：仿真实验。
- `sections/completed_work/07_supporting_proofs.tex`：正式附录 A，包含符号说明和证明。
- `figs/completed_work/`：原报告实际引用的五幅 PDF 图；`references/`：原始两份文献库。

摘要、最终结论、成果清单、致谢在源报告中缺失，已明确标为待补；独立“人工智能使用声明”章已按学校毕业论文规范删除，原创性声明页采用学校 2025 版含 AI 标注条款的标准声明文本。保留原文的“尚未开展”“后续拟”等阶段措辞；没有将研究计划改成已完成成果。关键词为依据正文提取的初步配置。

本目录的 `.cls/.cfg` 和文献样式保留第三方版权，见 `License`。此稿迁移的是已有内容与格式，不代表毕业论文研究已完成，也未重新核验原报告中的科学结论或引用事实。
