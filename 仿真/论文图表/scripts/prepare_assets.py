"""从已核对的C++输出自动生成论文表格，保存来源哈希。"""
import csv
from decimal import Decimal, ROUND_HALF_UP
import json
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent/'Gordon基准'
sys.path.insert(0,str(BASE/'scripts'))
from pipeline.common import atomic_json,command,digest_file
from paper_plots import create,read,LABELS
from prepare_density import prepare as prepare_density
RUN=BASE/'runs'/(BASE/'runs/LATEST').read_text().strip();DATA=ROOT/'data'
dataset=json.loads((RUN/'dataset.json').read_text())
(DATA/'truth_index.csv').write_text('truth_path\n'+''.join(str(Path(dataset['directory'])/t['truth'])+'\n' for t in dataset['trials']))
subprocess.run(command(BASE/'build/paper_statistics',truth_index=DATA/'truth_index.csv',summary=RUN/'summary.csv',
                      timing_index=DATA/'timing/index.csv',output=DATA),check=True)
for name in ['config.json','dataset.json','summary.csv','time_series.csv']:
    shutil.copy2(RUN/name,DATA/name)
rows=read(DATA/'accuracy.csv');times=read(DATA/'runtime.csv')
selected=[r for r in rows if (r['algorithm']=='ekf' or r['n']=='500') and (r['algorithm']!='etpf' or float(r['epsilon'])==1)]
lookup={(r['algorithm'],int(r['interval'])):r for r in selected}
best={m:min(float(lookup[(alg,m)]['rmse']) for alg in LABELS) for m in [1,2,4,8]}
lines=[r'\begin{tabular}{lcccc}',r'\toprule',r'算法 & $m=1$ & $m=2$ & $m=4$ & $m=8$ \\',r'\midrule']
for alg in LABELS:
    cells=[]
    for m in [1,2,4,8]:
        r=lookup[(alg,m)];v=float(r['rmse']);lo=v-float(r['ci_low']);hi=float(r['ci_high'])-v
        center='%.2f'%v;relative='%.2f'%float(r['nrmse_percent'])
        if v==best[m]: center=r'\mathbf{'+center+'}';relative=r'\mathbf{'+relative+'}'
        cells.append(r'\begin{tabular}[c]{@{}c@{}}$%s_{-%.2f}^{+%.2f}$\\$(%s\%%)$\end{tabular}'%(center,lo,hi,relative))
    lines.append(LABELS[alg]+' & '+' & '.join(cells)+r' \\[2pt]')
lines += [r'\bottomrule',r'\end{tabular}']
(DATA/'accuracy_table.tex').write_text('\n'.join(lines)+'\n')
reference=[r for r in times if r['n'] in ('0','500')]
minimum=min(float(r['step_us_mean']) for r in reference)
lines=[r'\begin{tabular}{lrrr}',r'\toprule',r'算法 & 每步内核时间 $\downarrow$ ($\mu$s) & 相对误差 $\downarrow$ (\%) & 未收敛率 $\downarrow$ \\',r'\midrule']
for alg in LABELS:
    r=next(t for t in reference if t['algorithm']==alg)
    number='%.3f'%float(r['step_us_mean'])
    if float(r['step_us_mean'])==minimum: number=r'\mathbf{'+number+'}'
    relative='%.2f'%float(lookup[(alg,1)]['nrmse_percent'])
    if alg=='bpf': relative=r'\mathbf{'+relative+'}'
    lines.append(LABELS[alg]+r' & $%s\pm %.3f$ & $%s$ & %s \\'%(number,float(r['step_us_sd']),relative,
        str(Decimal(lookup[(alg,1)]['ot_nonconverged_percent']).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))+r'\%' if alg=='etpf' else '--'))
lines += [r'\bottomrule',r'\end{tabular}']
(DATA/'runtime_table.tex').write_text('\n'.join(lines)+'\n')
font=create(dataset)
prepare_density()
atomic_json(DATA/'provenance.json',{'run':RUN.name,'sources':{name:digest_file(RUN/name) for name in ['summary.csv','time_series.csv','config.json','dataset.json']},
    'serial_timing_index':digest_file(DATA/'timing/index.csv'),'statistics_executable':digest_file(BASE/'build/paper_statistics'),
    'kde_reference':digest_file(DATA/'kde/provenance.json'),
    'bayes_reference':{p.name:digest_file(p) for p in DATA.glob('bayes_*.csv')},
    'statistics_source':digest_file(BASE/'apps/paper_statistics.cpp'),
    'font':font,'scripts':{p.name:digest_file(p) for p in Path(__file__).parent.glob('*.py')}})
print('论文图表与数据已生成')
