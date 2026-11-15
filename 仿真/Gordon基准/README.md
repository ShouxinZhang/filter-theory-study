# Gordon 基准：EKF，BPF，EnKF 与熵正则 ETPF

论文第 4.1 至 4.3 节的实验代码。论文采用 `configs/quick.json`（8 条轨迹，100 步），该次运行的汇总结果保存在 `results/quick-eb95c99ee644/`；重新运行后精度类数值逐位一致。

实现固定数据 → 在线滤波 → 独立评估 → 图表与报告，详细模块地图见 [PLAN.md](PLAN.md)
Gordon 主实验使用 EKF，BPF，EnKF，Sinkhorn-ETPF，标准 KF 在 linear 配置和数学测试中验证

已完成 [Gordon较小消融](results/quick-eb95c99ee644/report.md) 的608作业和线性高斯验证的360作业，均无失败，完整100条×400步网格尚未运行

快速开始

~~~bash
python3 scripts/run.py --config configs/smoke.json --jobs 1
python3 scripts/run.py --config configs/quick.json --jobs 8
~~~

完整网格和标准 KF 验证

~~~bash
python3 scripts/run.py --config configs/full.json --jobs 8
python3 scripts/run.py --config configs/linear.json --jobs 1
~~~

首次执行自动 CMake Release 构建并运行测试，需要 C++17，CMake，Ninja，Eigen3
调度使用 Python 标准库，绘图自动寻找已有 matplotlib/numpy 环境，也可用 BASELINE_PLOT_PYTHON 指定，不创建重复虚拟环境
相同源码，二进制和配置会恢复已有运行，每条轨迹的完成状态和内容哈希保存在 status.json，已完成输出未变时不会重跑
若仅重建图表，先执行 cmake --build build --target time_series，再使用绘图环境执行 scripts/report.py runs/<run_id>，无需重新滤波
报告刷新会核对冻结真值与滤波输出哈希，再调用 C++ time_series 评估器计算时序误差，Python 只负责调度和绘图
中文使用宋体 SimSun，英文数字使用 Times New Roman，输出300 dpi PNG与字形转路径的SVG，数学变量与上下标使用 MathText/STIX 渲染，中文与公式混排显式保留宋体，字体路径及哈希记录于 report_metadata.json
默认字体为 /usr/local/share/fonts/simsun.ttc 和 /usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf，可用 BASELINE_CHINESE_FONT 与 BASELINE_LATIN_FONT 指定；缺少宋体会报错，缺少英文字体时回退 STIXGeneral 并记录实际字体

输出位置

- data/<dataset_id>/manifest.json 固定数据说明与文件哈希，observations.csv 和 truth.csv 分离保存
- runs/<run_id>/jobs/<config_id>/trial_XXXX/filter.csv 在线估计，区间，内核计时与 OT 诊断
- 同目录 metrics.csv 为 C++ 独立评估结果，filter.csv.runtime.csv 为端到端耗时和峰值 RSS
- runs/<run_id>/summary.csv 汇总 RMSE，轨迹 bootstrap 区间，观测前后指标和求解状态
- runs/<run_id>/time_series.csv 保存各配置逐时刻跨轨迹 RMSE，预测 RMSE，累计 RMSE，观测标记与有效轨迹数，补充评估版本保存在 time_series_metadata.json
- runs/<run_id>/report.md 与 figures/ 为自动报告，runs/LATEST 记录最近完成运行
- 每个运行保存 metadata.json，配置，基准清单，源码快照和 SHA256，日志位于各作业目录

独立调用示例

~~~bash
build/generate --model gordon --steps 100 --seed 42 --observations /tmp/demo/observations.csv --truth /tmp/demo/truth.csv
build/filter --model gordon --algorithm etpf --observations /tmp/demo/observations.csv --n 100 --epsilon 1 --interval 4 --seed 123 --output /tmp/demo/filter.csv
build/evaluate --truth /tmp/demo/truth.csv --filter /tmp/demo/filter.csv --common-interval 8 --output /tmp/demo/metrics.csv
~~~

方法和解释

- Gaussian 分布参数采用方差，真值初值默认 N(0,2)，过程噪声 N(0,10)，观测噪声 N(0,1)，--fixed-initial 1 可生成初值0.1的原例
- 降低帧率只屏蔽观测，状态过程保持每步演化，滤波接口没有真值参数，也不能读取未来数据
- BPF 使用先验提议和系统重采样，EnKF 使用扰动观测，三个集合方法共享初始和过程随机数流的种子规则
- 随机数引擎为 mt19937_64，normal_distribution 的实现可能随标准库改变，跨平台复用冻结数据，不依赖种子保证逐位一致
- ETPF 使用一维平方代价，单调精确 OT 的可行对偶势只初始化缩放势，不直接用 LP 结果代替 Sinkhorn
- 稳定化 Sinkhorn 在缩放过大或过小时吸收到对数势，epsilon 始终为配置值，没有暗中归一化代价
- 每次最终耦合进行行列缩放和秩一补全以恢复边缘，sinkhorn_residual 是修正前残差，rounding_l1 是修正幅度，sinkhorn_converged 明确标记原求解是否达到容差
- 达到最大迭代次数但未收敛的结果仍参加统计并在报告中标记，不能把该曲线当作精确熵正则解的性能
- 后验区间取重采样前的加权经验分位点，EnKF 取更新集合分位点，KF/EKF 取高斯等尾区间，均不声称为多峰 HPD
- 主 RMSE 是合并全部误差平方后开方，95%置信区间由 C++ 对整条轨迹 bootstrap 计算，失败作业保留日志并显式减少有效样本数
- 时序 RMSE 在每个状态步对独立轨迹的误差平方求平均后开方，不平滑；无观测步取预测输出，观测步取更新后输出，累计 RMSE 另图展示，末值等于主 RMSE
- 时序图按观测间隔分面，采用配置中预设的代表 N 与 epsilon，同时保留完整线性纵轴和对数纵轴版本，所有参数组合的时序结果均写入 CSV
- --jobs 大于1用于精度实验吞吐，耗时只能作并发环境诊断，严格速度比较请以 --jobs 1 串行运行并保持机器负载稳定
- C++ 内核计时包含预测或更新所需的估计统计，不包括文件读写和绘图，末步输出时间和内存另行记录

参考数学与实现说明，代码为本任务独立实现

- [Gordon等1993](https://doi.org/10.1049/ip-f-2.1993.0015)
- [POT稳定化Sinkhorn说明](https://pythonot.github.io/gen_modules/ot.bregman.html#ot.bregman.sinkhorn_stabilized)
- [Altschuler等的可行化算法](https://arxiv.org/html/1705.09634#S2)

轨迹图以共享时间轴的状态与观测子图展示首条轨迹，紫色点是当前帧率下实际使用的观测，灰色叉号是被屏蔽的原始观测，黑线是无噪声观测参考；生成时核对观测文件哈希和滤波输出的观测掩码

最优在线滤波参考

[网格积分与模型风险估计](runs/quick-eb95c99ee644/grid_reference/report.md)比较原8条轨迹上的高精度后验均值与BPF，另用独立512条×100步估计每步观测的Bayes最优风险；该近似参考不参与原四算法的速度排名

~~~bash
python3 scripts/grid_reference.py --manifest runs/quick-eb95c99ee644/dataset.json --output runs/quick-eb95c99ee644/grid_reference
python3 scripts/grid_reference.py --manifest runs/quick-eb95c99ee644/grid_reference/monte_carlo/dataset.json --output runs/quick-eb95c99ee644/grid_reference/monte_carlo --cases 60:0.2,60:0.1
python3 scripts/grid_reference_report.py runs/quick-eb95c99ee644
~~~
