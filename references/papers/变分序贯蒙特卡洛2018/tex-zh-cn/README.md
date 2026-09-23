# 变分序贯蒙特卡洛——中文译稿

arXiv:1705.11140v2 全文及补充材料，中文 PDF 共 22 页。末尾“翻译说明”集中记录 6 项经核实的修订；公式、图表、算法、文献编号与引用身份保留。数学使用 bm、正体 tr 和微分 d。

## 编译

依赖 XeLaTeX、latexmk、模板所需 TeX Live 宏包、Fandol/TeX Gyre Pagella 字体及带 PyMuPDF 的 Python：

    bash build.sh ../build

若系统 Python 未安装 PyMuPDF，可用环境变量 QTM_PYTHON 指定现有解释器。构建目录必须在源码目录之外。无原始 PDF、原包或绝对路径依赖，不启用 shell-escape。

main.tex 仅组合模块；sections/ 保存正文，sections/supplement/ 保存四个补充小节；assets/figures/ 为 14 个原始矢量资产；bibliography/entries.tex 保留 48 条原书目；audit/ 保存台账和核验结果。

## 排版与文字层

沿用技能蓝色中文单栏模板，原图刻度和图例保留英文，中文含义见图注及翻译说明。build.sh 自动规范化 PDF 文本矩阵以改善 Evince 拖选，并检查字形编码、次序与坐标（误差小于 0.001 pt），每页在固定的 144/216/72/96 dpi 中至少一个分辨率下像素严格相同，链接和书签不变。复杂数学混排复制仍可能受阅读器限制。

数学修订的代数依据见书末；有限二态模型全枚举检验见 audit/math.json。未复现原实验，不声称穷尽原稿错误。
