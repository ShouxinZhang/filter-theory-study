#!/usr/bin/env python3
"""将 C++ 网格积分与独立风险评价结果汇编为中文报告。"""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path
from pipeline.common import ROOT, atomic_json, command, digest_file, source_files


def read(path):
    with Path(path).open() as stream:
        return list(csv.DictReader(stream))


def main(run_dir):
    run_dir = Path(run_dir).resolve()
    base = run_dir / 'grid_reference'
    dataset = json.loads((run_dir / 'dataset.json').read_text())
    config = json.loads((run_dir / 'config.json').read_text())
    bpf_config = next(row['config_id'] for row in read(run_dir / 'summary.csv')
                      if row['algorithm'] == 'bpf' and int(row['n']) == config['reference_n'] and row['interval'] == '1')
    # 复用独立 C++ 评价器得到相同基准下的 BPF 归一化误差。
    index = base / 'bpf_index.csv'
    with index.open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n'); writer.writerow(['truth_path','filter_path'])
        for trial in dataset['trials']:
            writer.writerow([Path(dataset['directory']) / trial['truth'],
                run_dir / 'jobs' / bpf_config / ('trial_%04d' % trial['trial']) / 'filter.csv'])
    subprocess.run(command(ROOT/'build/grid_risk', index=index, output=base/'bpf_risk.csv'), check=True)
    original = read(base/'m1_L80_dx0.05/risk.csv')[-1]
    bpf = read(base/'bpf_risk.csv')[-1]
    mc = base/'monte_carlo/m1_L60_dx0.1'
    risk, ci = read(mc/'risk.csv')[-1], read(mc/'risk.csv.ci.csv')[0]
    lines = ['Gordon 每步观测的最优在线滤波参考', '',
        '当前模型与原基准一致，初值方差2，过程噪声方差10，观测噪声方差1，每步观测，统计前100步，不含未来观测或平滑。', '',
        '最优的含义', '',
        r'平方损失下，最优在线估计是后验均值。其 MSE 等于后验方差的期望，见 [Särkkä 与 Svensson 的教材](https://users.aalto.fi/~ssarkka/pub/bfs_book_2023_online.pdf)。',
        '$$', r'\begin{aligned}',
        r'&\widehat x_k^{\star}=\mathbb E[x_k\mid y_{1:k}],\\',
        r'&R_k^{\star}=\mathbb E[\operatorname{Var}(x_k\mid y_{1:k})],\\',
        r'&\mathrm{NRMSE}_{\star}=\sqrt{\frac{\sum_{k=1}^{T}R_k^{\star}}{\sum_{k=1}^{T}\mathbb E[x_k^2]}}.',
        r'\end{aligned}', '$$',
        '这里归一化的是总体期望平方误差与总体状态二阶矩之比，不是每条样本相对误差比值的期望。有限测试集上，某算法偶尔低于后验均值的经验误差不构成理论矛盾。', '',
        '数值结果', '',
        '| 统计对象 | RMSE或风险平方根 | 相对误差 |', '|---|---|---|',
        '| 原8条轨迹，网格后验均值的实际误差 | %.6f | %.4f%% |' % (float(original['rmse']),100*float(original['nrmse'])),
        '| 原8条轨迹，BPF，粒子数%s | %.6f | %.4f%% |' % (config['reference_n'],float(bpf['rmse']),100*float(bpf['nrmse'])),
        '| 独立512条轨迹，基于后验方差的模型风险估计 | %.6f | %.4f%% |' % (float(risk['conditional_risk_root']),100*float(risk['conditional_risk_ratio'])),
        '| 上述风险估计的近似95%%蒙特卡洛置信区间 | [%.6f, %.6f] | [%.4f%%, %.4f%%] |' %
            (float(ci['risk_root_ci_low']),float(ci['risk_root_ci_high']),100*float(ci['relative_ci_low']),100*float(ci['relative_ci_high'])), '',
        '512条轨迹使用独立种子730001起，每条100步。置信区间由C++以整条独立轨迹为单位，用delta-method计算，归一化分子与分母的相关性已计入，区间不包含网格截断和离散误差。',
        '当前BPF在同一组8条轨迹上已接近高精度后验均值参考，四成多的相对误差不能全部归因于粒子数或算法实现。该结果只适用于这里的模型，初值，噪声，100步统计窗口与每步观测设置。', '',
        '网格核对', '',
        '| 数据 | 积分半宽 | 网格间距 | 实际RMSE | 后验风险平方根 | 最大预测质量偏差 |', '|---|---|---|---|---|---|']
    for label, folder in [('原8条',base),('独立512条',base/'monte_carlo')]:
        for path in sorted(folder.glob('m1_L*_dx*')):
            total=read(path/'risk.csv')[-1]; diagnostic=read(path/'diagnostics.csv')[0]
            bound,spacing=path.name.split('_')[1:]
            lines.append('| %s | %s | %s | %.10f | %.10f | %.3g |' % (label,bound[1:],spacing[2:],
                float(total['rmse']),float(total['conditional_risk_root']),float(diagnostic['max_prediction_mass_error'])))
    lines += ['', '网格按梯形求积计算预测密度与似然更新，保留双峰后验，不做高斯近似，不使用粒子重采样。有限网格仍是数值近似，质量偏差接近机器精度并不单独证明全部积分误差为零，因此同时核对网格加密与扩大区间。',
        '参考实现通过线性高斯解析KF校验，未来观测隔离校验和独立风险评价手算校验。原基线滤波输出与汇总不变。', '',
        '复现与数据', '',
        '- [原数据网格参考](m1_L80_dx0.05/risk.csv)，[BPF同数据评价](bpf_risk.csv)',
        '- [独立数据风险估计](monte_carlo/m1_L60_dx0.1/risk.csv)，[置信区间](monte_carlo/m1_L60_dx0.1/risk.csv.ci.csv)',
        '- [独立数据及种子清单](monte_carlo/dataset.json)，[源码与环境记录](metadata.json)',
        '- C++入口为 apps/grid_reference.cpp 与 apps/grid_risk.cpp，积分实现位于 src/reference/grid_reference.cpp；Python调度脚本为 scripts/grid_reference.py，报告脚本为 scripts/grid_reference_report.py。']
    (base/'report.md').write_text('\n'.join(lines)+'\n')
    snapshot=base/'source'; snapshot.mkdir(exist_ok=True)
    hashes={}
    for p in source_files():
        target=snapshot/p.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target); hashes[str(p.relative_to(ROOT))]=digest_file(p)
    atomic_json(base/'metadata.json', {'environment':json.loads((run_dir/'metadata.json').read_text())['environment'],
        'environment_scope':'引用同机原基线的硬件与软件环境，其中parallel_jobs和timing_mode属于原基线，不代表本参考计算；参考不用于速度排名',
        'source':hashes, 'binaries':{name:digest_file(ROOT/'build'/name) for name in ['generate','grid_reference','grid_risk']},
        'dataset':digest_file(base/'dataset.json'),'independent_dataset':digest_file(base/'monte_carlo/dataset.json'),
        'scope':'每步观测，前100步，风险比值按总体二阶矩归一化，蒙特卡洛为512条独立轨迹'})
    print(base/'report.md')

if __name__=='__main__':
    main(sys.argv[1])
