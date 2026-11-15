滤波基准实验报告

运行标识，$run_id
状态，$status

实验与数据

$config_text

环境记录

$environment_table

计时口径，$timing_mode，预测与更新内核单独计时，读盘，写盘，诊断快照及报告生成不计入内核，端到端运行时间另存每条轨迹的 runtime.csv

结果摘录，固定展示参数，不按测试误差选择最优配置

$metrics_table

完整结果见 [summary.csv](summary.csv)，作业状态见 [jobs.json](jobs.json)，冻结基准清单见 [dataset.json](dataset.json)

$figure_style

RMSE 时序

$time_series_definition

![逐时刻跨轨迹RMSE，对数纵轴](figures/rmse_time_log.png)

对数纵轴便于同时查看误差尖峰和较小误差，数据未截断，另保留 [完整线性纵轴图](figures/rmse_time.png)，[线性图SVG](figures/rmse_time.svg)，[对数图SVG](figures/rmse_time_log.svg) 和 [时序数据](time_series.csv)

![截至当前时刻的累计RMSE](figures/rmse_cumulative.png)

累计曲线在当前时刻及之前的所有误差平方上汇总后开方，其末值等于 summary.csv 的全时域 RMSE，与逐时刻 RMSE 分开绘制

![帧率消融](figures/rmse_rate.png)

![粒子数消融](figures/rmse_particles.png)

![正则强度与帧率](figures/epsilon_rate.png)

![运行时间与收敛](figures/runtime_convergence.png)

![同一条轨迹与实际观测](figures/trajectory.png)

$trajectory_description

求解与实验限制

$diagnostics

初始分布，过程噪声，观测噪声均为 Gaussian，Gordon 使用 EKF 而非标准线性 KF，EnKF 为扰动观测版本，BPF 使用系统重采样
ETPF 使用未归一化平方代价，单调一维 OT 对偶势仅作 Sinkhorn 初值，最终仍求指定 $$\varepsilon$$ 的熵正则目标，可行化修正保持边缘，未达到容差的更新仍明确标记
报告中的置信区间由 C++ 对完整轨迹进行 bootstrap 得到，观测前后 RMSE 使用各自观测时刻，共同观测时刻指标在 CSV 中单列
主 RMSE 包含所有完成轨迹的所有状态步，未收敛的 ETPF 更新并未删除，若发生失败作业，对应配置样本数会减少，应先排查再比较
等尾区间覆盖率不是多峰后验的 HPD 覆盖率，有限粒子误差，正则偏差，求解误差和重心投影误差不能仅靠一条 RMSE 曲线分离
