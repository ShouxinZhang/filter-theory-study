# 论文图表的生成

论文第 4 章全部图表的生成脚本与所用数据。脚本只做汇总与绘图，数值来自同级目录的三个实验。

| 论文中的图表 | 脚本 | 数据来源 |
| --- | --- | --- |
| 表 4-2（精度与串行开销），表 4-3（不同观测间隔的误差） | `scripts/prepare_assets.py` | `../Gordon基准` 的运行结果，`scripts/benchmark_serial.py` 的串行计时 |
| 图 4-1（逐时刻 RMSE），图 4-2（轨迹），图 4-3（消融与耗时） | `scripts/paper_plots.py`（由 `prepare_assets.py` 调用） | 同上 |
| 图 4-4（后验密度） | `scripts/prepare_density.py`（由 `prepare_assets.py` 调用） | 同上 |
| 表 4-4（四项误差） | `scripts/logistic_plots.py` | `data/logistic/`，取自 `../Logistic零过程噪声/runs/` |
| 图 4-5（Logistic），图 4-6（指标曲线），图 4-7（粒子示例） | `scripts/render_ml_figs.py` | `data/logistic/` 与 `../数字识别/outputs/` |

## 复现

```bash
python3 ../Gordon基准/scripts/run.py --config ../Gordon基准/configs/quick.json --jobs 8
```

```bash
python3 scripts/benchmark_serial.py
```

```bash
python3 scripts/prepare_assets.py
```

```bash
python3 scripts/render_ml_figs.py
```

- 前三步依次完成 Gordon 基准的运行，串行计时与图表生成；脚本读取 `../Gordon基准/runs/LATEST` 指向的运行。
- `render_ml_figs.py` 须先在 `../数字识别` 运行 `run.py` 得到网络检查点，并需要显卡。
- 绘图需要 matplotlib 与 numpy；中文字体优先使用宋体，缺失时退回 Noto Serif CJK SC。
- 图写入 `figures/`，拷入论文的 `figs/completed_work/` 即可。

## 说明

- `data/` 与 `figures/` 中保存的是论文所用的那一次结果。重新运行后，精度类数值逐位一致；计时类数值（表 4-2 的每步耗时）会随机器状态有百分之一量级的波动。
- `logistic_plots.py` 也会画一版 Logistic 图；论文采用的是 `render_ml_figs.py` 生成的版本，二者数据相同，只是字号不同。
- `data/` 下若干 `provenance.json` 记录了生成当时的源码路径与指纹，路径是当时的工作目录，仅作历史记录。
- `LOG.md` 是图表历次修改的记录。
