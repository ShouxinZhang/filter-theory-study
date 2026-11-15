# 链表示例（原生无 `.cls` 混合笔记案例）

本目录保存《链表：结构，操作与复杂度》的纯源文件（`src/`），展示不依赖外部 LaTeX 文档类的原生混合长卷写法：
- 章节可折叠目录，4 个编号公式，命题与证明，三线表
- 3 张 TikZ 图（`figs/singly.tex`，`figs/insert.tex`，`figs/doubly.tex`）与 3 个 `algpseudocode` 算法框（`algs/*.tex`）
- 图与算法内部通过 `\cref{...}` 双向引用正文中的公式，算法与命题（支持点击跳转，悬停预览与 `Ctrl+Click` 源码定位）

## 编译与双栏实时预览（输出到 `.agents/.tmp` 避免污染仓库）

```bash
S=.agents/skills/chores/html-tex-doc/scripts/html_tex_doc.py
OUT=.agents/.tmp/html-tex-doc-linked-list

# 仅静态构建
python3 $S build \
  --src .agents/skills/chores/html-tex-doc/references/examples/linked-list/src \
  --build-dir $OUT/build \
  --out $OUT/site

# 启动实时预览与 Web 双栏编辑工作台（Ctrl+\ 开合双栏，Ctrl+Click 双向高亮对齐）
python3 $S serve \
  --src .agents/skills/chores/html-tex-doc/references/examples/linked-list/src \
  --build-dir $OUT/build \
  --out $OUT/site \
  --port 18767
```
