"""用随包 CSV 重新绘制两张汇报图，不重新运行实验。
运行：uv run --with matplotlib python research/prepare_simulation_figures.py
"""
from pathlib import Path
import csv, json, hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'research/simulation-data'; OUT=ROOT/'talks/filtering/public/simulation'
DATA.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
def read(path):
    with path.open() as f:return list(csv.DictReader(f))
def write(path,rows):
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader();w.writerows(rows)
ids={'EKF':'ekf_n0_e0_m1','BPF':'bpf_n500_e0_m1','EnKF':'enkf_n500_e0_m1','ETPF':'etpf_n500_e1_m1'}
rows=read(DATA/'rmse-m1.csv')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.labelsize':12,'legend.fontsize':10,'svg.fonttype':'path'})
colors={'EKF':'#526174','BPF':'#147bab','EnKF':'#d68426','ETPF':'#218b79'}
styles={'EKF':'-','BPF':'--','EnKF':'-.','ETPF':':'}
def finish(ax):
    ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.18);ax.set_axisbelow(True)
fig,ax=plt.subplots(figsize=(5.7,3.15),layout='constrained')
for name,key in ids.items():
    part=[r for r in rows if r['config_id']==key]
    ax.plot([int(r['step']) for r in part],[float(r['rmse']) for r in part],label=name,color=colors[name],linestyle=styles[name],linewidth=1.65)
ax.set(xlabel='State step k',ylabel='RMSE',yscale='log',xlim=(1,100));ax.legend(ncol=4,loc='upper center',bbox_to_anchor=(.5,1.2),frameon=False,columnspacing=1,handlelength=2);finish(ax)
fig.savefig(OUT/'rmse-m1.svg');plt.close(fig)
fig,ax=plt.subplots(figsize=(5.7,3.15),layout='constrained')
for name in ['BPF','EnKF','ETPF']:
    part=read(DATA/(name.lower()+'-k11.csv'))
    ax.plot([float(r['x']) for r in part],[float(r['kde']) for r in part],label=name,color=colors[name],linestyle=styles[name],linewidth=1.9)
ax.plot([float(r['x']) for r in part],[float(r['ekf_gaussian']) for r in part],label='EKF',color='#b53b40',linestyle='--',linewidth=1.65)
meta=json.loads((DATA/'provenance.json').read_text());truth=meta['selection']['truth']
ax.axvline(truth,color='#454545',linestyle=':',label='Truth',linewidth=1.4)
ax.set(xlabel='State x',ylabel='Density',ylim=(0,None));ax.legend(ncol=3,loc='upper right',frameon=False,columnspacing=1);finish(ax)
fig.savefig(OUT/'posterior-k11.svg');plt.close(fig)
print('Prepared RMSE m=1 and posterior k=11 from bundled data.')
