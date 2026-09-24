# 自编码变分贝叶斯 · 中文 TeX

来源：arXiv:1312.6114v11，Kingma 与 Welling，Auto-Encoding Variational Bayes。
使用翻译技能的蓝色中文单栏模板，正文、附录 A–F、图注和算法完整翻译，保留原图和原始书目。已确认的公式及表述修正见文末“翻译说明”。

## 编译

在本任务 sandbox 内，将构建目录设为源码目录外的独立目录：

    bash build.sh /absolute/path/to/task-sandbox/output/debug/my-build

构建脚本使用 XeLaTeX、latexmk，并通过 Python + PyMuPDF 规范化文本定位，以改善 Evince 中的选择顺序；会比较逐页字形坐标、渲染、链接和书签。输出 my-build/main.pdf。已有构建目录必须属于当前工程。
依赖：TeX Live（ctex、fontspec、TikZ、amsmath、bm、natbib、algorithm/algpseudocode 等），TeX Gyre Pagella 和 Fandol 字体，以及 PyMuPDF。脚本优先寻找仓库共享环境；也可设置 QTM_PYTHON=/path/to/python。不会自动安装依赖或启用 shell-escape。

## 模块

- main.tex：入口；metadata.tex：标题与作者。
- sections/：分节正文、六个附录及翻译说明。
- assets/figures/：官方图件，未重绘；图内英文标签保留。
- bibliography/：原始书目与渲染设置。
- style/：原版蓝色模板、中文对象名、原文数学宏。
- tools/：PDF 文字定位规范化脚本。

所有产物默认仅保存在本任务 sandbox 内。
