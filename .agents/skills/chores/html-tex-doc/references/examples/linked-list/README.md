# 链表示例（HTML 正文 + TeX 出图完整案例）

本目录保存《链表：结构、操作与复杂度》的纯源文件（`src/`），涵盖：
- 章节目录、4 个编号公式、命题 + 证明、三线表；
- 3 张 TikZ 图（`figs/singly.tex`、`figs/insert.tex`、`figs/doubly.tex`）与 3 个 `algpseudocode` 算法框（`algs/*.tex`）；
- 图与算法内部通过 `\cref{...}` 双向引用正文中的公式、算法与命题（支持点击跳转与悬停预览）。

## 编译与本地预览（输出到 `.agents/.tmp` 避免污染仓库）

```bash
S=.agents/skills/chores/html-tex-doc/scripts/html_tex_doc.py
OUT=.agents/.tmp/html-tex-doc-preview

python3 $S build \
  --src .agents/skills/chores/html-tex-doc/references/examples/linked-list/src \
  --build-dir $OUT/build \
  --out $OUT/site

python3 -m http.server 18767 --bind 127.0.0.1 -d $OUT/site
# 浏览器访问 http://127.0.0.1:18767/
```
