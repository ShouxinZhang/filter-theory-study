# hithesis 学位论文薄适配器示例（外部 `.cls` 接入范式）

本示例展示如何在不向通用构建引擎硬编码学校模板宏的前提下，为 `hithesis` 等外部 LaTeX `.cls` 学位论文提供受控 Markdown + Web 双栏实时预览能力。

## 解耦边界

| 层级 | 文件位置 | 职责 |
| --- | --- | --- |
| 论文特定导入器 | 项目本地 `import_tex.py` | 一次性或按需剥离 `.cls` 私有宏（如 `\hit@appendix@chapter*`，`cabstract`），将 `\chapter` / `equation` / `theorem` 转为 `src/*.md`，将 `algorithm2e` 拆为 `src/algs/*.tex` |
| 通用学术骨架 | `src/alg2e.tex`，`src/macros.tex`，`src/refs.bib` | 同源数学宏，`algorithm2e` 独立编译头与 BibTeX 文献库 |
| 通用编译与双栏工作台 | `html-tex-doc/scripts/html_tex_doc.py` | 多文件受控 Markdown 编译，可折叠目录，Web 双栏编辑器，全文搜索与 `Ctrl+Click` 双向高亮对齐 |

## 快速体验（输出到 `.agents/.tmp` 避免污染仓库）

```bash
S=.agents/skills/chores/html-tex-doc/scripts/html_tex_doc.py
EX=.agents/skills/chores/html-tex-doc/references/examples/hithesis-adapter
OUT=.agents/.tmp/html-tex-doc-hithesis

# 静态构建验证
python3 $S build --src $EX/src --build-dir $OUT/build --out $OUT/site

# 启动双栏实时预览（浏览器访问 http://127.0.0.1:18767）
python3 $S serve --src $EX/src --build-dir $OUT/build --out $OUT/site --port 18767
```

若要体验从 `tex_demo/` 重新导入到临时目录，可复制本目录到 `$OUT/work` 后执行 `python3 $OUT/work/import_tex.py`。
