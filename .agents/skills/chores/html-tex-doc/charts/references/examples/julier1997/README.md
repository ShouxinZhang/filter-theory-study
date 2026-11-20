# Julier & Uhlmann (1997) 6 张中文数据图范例

本目录包含 Julier & Uhlmann (1997) *New Extension of the Kalman Filter to Nonlinear Systems*（SPIE Vol. 3068, pp. 182–193）两个经典基准算例的确定性仿真与出图范例：

- 算例 1：极坐标到直角坐标变换均值与 $1\sigma$ 误差椭圆对比，以及缩放参数 $\kappa$ 精度扫描（`fig1`、`fig2`）。
- 算例 2：5 维高超声速再入飞行器地面雷达追踪（`fig3` 至 `fig6`）。

## 运行方式

```bash
E=.agents/skills/chores/html-tex-doc/charts/references/examples/julier1997

python3 $E/simulate_julier1997.py --out-dir /tmp/julier1997_demo
python3 $E/build_julier_charts.py --sim /tmp/julier1997_demo/sim_data.json --out-dir /tmp/julier1997_demo/figs
```
