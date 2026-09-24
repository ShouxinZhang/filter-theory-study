# 重要性加权自编码器：简体中文译稿

依据用户提供的 arXiv:1509.00519v4 源码及对应 PDF，原作者为 Yuri Burda、Roger Grosse、Ruslan Salakhutdinov。
原始来源：https://arxiv.org/abs/1509.00519v4 。译文不代表作者认可；原文修正详见末尾“翻译说明”。

## 编译

需要 TeX Live（XeLaTeX、latexmk、ctex、TikZ 等）、TeX Gyre Pagella/Fandol 字体，以及安装了 PyMuPDF 的 Python 3。
在源码目录运行，构建路径必须位于本任务 sandbox 内且与源码目录分离：

    ./build.sh ../build

已有 Python 环境可显式指定：

    QTM_PYTHON=/path/to/python ./build.sh ../build

最终 PDF 位于指定构建目录的 main.pdf，main.raw.pdf 是文本定位修复前的版本。脚本会比较修复前后的字形坐标、渲染、链接和书签。复用共享 Python 环境即可，无须复制环境到源码包。

## 模块

- main.tex、metadata.tex、config.tex：入口和元数据。
- sections/：正文、附录及翻译说明。
- bibliography/：保留原书目信息和作者年引用。
- style/：原始技能蓝色模板及数学宏。
- assets/figures/：原始图件；网络结构图保留为可编辑 TikZ。
- tools/：PDF 文本定位修复工具。

交付、修订与构建产物默认均留在当前 sandbox；不自动复制到 Downloads 或外部服务。数学粗体使用 bm，微分 d 用正体。位图内英文标签保留，正文和图注均已翻译。
