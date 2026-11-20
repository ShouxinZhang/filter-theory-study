# Gordon, Salmond, & Smith (1993) 11 张双语数据图范例

本目录展示如何将「纯数值仿真」与「调用 `htd_charts` 通用引擎出图」彻底解耦，完整复现 Gordon (1993) 一维非平稳非线性滤波算例（图 1 至图 4）与二维纯方位目标追踪算例（图 5 至图 11）的中英双语 22 张 SVG 与 22 张单页矢量 PDF。

## 运行方式

```bash
E=.agents/skills/chores/html-tex-doc/charts/references/examples/gordon1993

# 1. 生成确定性仿真数据 sim_data.json（输出到指定目录）
python3 $E/simulate_gordon1993.py --out-dir /tmp/gordon1993_demo

# 2. 基于 sim_data.json 渲染中英双语 SVG 与单页矢量 PDF
python3 $E/build_gordon_charts.py --sim /tmp/gordon1993_demo/sim_data.json --out-dir /tmp/gordon1993_demo
```

## 示例亮点

- 零 CSS/HTML 硬编码：全文件仅调用 `Chart` 链式接口并声明语义角色（`primary`，`secondary`，`accent`，`fg`）。
- 零人名术语门禁：中文版自动校验不出现违禁人名术语，满足仓库 `习惯.md` 规范。
- 主题一键切换：通过 `--theme <name>` 即可切换整套 22 张图的配色与排版风格。
