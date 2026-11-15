"""ICLR单栏宽度的仿真图，仅展示已有C++统计与冻结数据。"""
import csv
from pathlib import Path
import sys
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent/'Gordon基准'
sys.path.insert(0,str(BASE/'scripts'))
from plot_style import style, save, COLORS, LINESTYLES
RUN=BASE/'runs'/(BASE/'runs/LATEST').read_text().strip()
OUT=ROOT/'figures'
LABELS={'ekf':'EKF','bpf':'BPF','enkf':'EnKF','etpf':'ETPF'}

def read(path):
    with Path(path).open() as f: return list(csv.DictReader(f))

def export(fig,name,rect=None):
    save(fig,OUT,name+'.png',rect=rect)
    fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight')

def legends_below(fig,axes):
    """预留统一图例行，固定位置，避免自动选位遮住曲线。"""
    rect=(0,.15,1,1)
    fig.align_xlabels(axes)
    fig.tight_layout(rect=rect)
    for ax in axes:
        box=ax.get_position()
        handles,labels=ax.get_legend_handles_labels()
        fig.legend(handles,labels,loc='lower center',
                   bbox_to_anchor=((box.x0+box.x1)/2,.01),ncol=2,
                   fontsize=6,frameon=False,handlelength=1.8,
                   columnspacing=.7,handletextpad=.4,labelspacing=.25)
    return rect

def create(dataset):
    metadata=style()
    plt.rcParams.update({'font.size':8,'axes.labelsize':8,'axes.titlesize':8.5,'legend.fontsize':7,
                         'xtick.labelsize':7,'ytick.labelsize':7,'lines.linewidth':1,'pdf.fonttype':42})
    OUT.mkdir(parents=True,exist_ok=True)
    series=read(RUN/'time_series.csv')
    selected=[r for r in series if (r['algorithm']=='ekf' or r['n']=='500') and
              (r['algorithm']!='etpf' or float(r['epsilon'])==1)]
    fig,axes=plt.subplots(2,2,figsize=(5.5,3.15),sharex=True,sharey=True)
    for ax,m in zip(axes.flat,[1,2,4,8]):
        for alg in LABELS:
            p=[r for r in selected if r['algorithm']==alg and int(r['interval'])==m]
            ax.plot([int(r['step']) for r in p],[float(r['rmse']) for r in p],
                color=COLORS[alg],linestyle=LINESTYLES[alg],label=LABELS[alg])
        ax.set(yscale='log',ylim=(0.5,400),title=r'$m=%d$'%m,xlabel=r'状态步 $k$',ylabel=r'$\mathrm{RMSE}_k$')
        ax.tick_params(axis='x',labelbottom=True)
    axes[0,0].legend(ncol=4,loc='lower left',bbox_to_anchor=(-0.1,1.15),frameon=False)
    export(fig,'rmse_time')
    # 将实际观测与状态分开定标，黑线对应已知真值的无噪声观测映射。
    directory=Path(dataset['directory']);trial=dataset['trials'][0]
    truth=read(directory/trial['truth']);obs=read(directory/trial['observations']);k=[int(r['step']) for r in truth]
    fig,axes=plt.subplots(2,1,figsize=(5.5,1.85),sharex=True,gridspec_kw={'height_ratios':[1.3,1]})
    axes[0].plot(k,[float(r['x']) for r in truth],color='black',label=r'真实状态 $x_k$')
    for alg in ('bpf','enkf','etpf'):
        cfg=next(r['config_id'] for r in selected if r['algorithm']==alg and r['interval']=='1')
        records=read(RUN/'jobs'/cfg/'trial_0000/filter.csv')
        axes[0].plot(k,[float(r['post_mean']) for r in records],color=COLORS[alg],linestyle=LINESTYLES[alg],label=LABELS[alg])
    axes[0].set(ylabel=r'$x_k$');axes[0].legend(ncol=4,loc='lower left',bbox_to_anchor=(-.05,1),frameon=False)
    axes[1].plot(k,[float(r['x'])**2/20 for r in truth],color='black',label=r'$x_k^2/20$')
    axes[1].scatter(k,[float(r['y']) for r in obs],c='#9333ea',s=5,label=r'实际观测 $y_k$')
    axes[1].set(xlabel=r'状态步 $k$',ylabel=r'$y_k$');axes[1].legend(ncol=2,fontsize=6,loc='upper right')
    export(fig,'trajectory')
    accuracy=read(ROOT/'data/accuracy.csv');timing=read(ROOT/'data/runtime.csv')
    fig,axes=plt.subplots(1,3,figsize=(5.5,1.9))
    for alg in ('bpf','enkf','etpf'):
        p=sorted([r for r in accuracy if r['algorithm']==alg and r['interval']=='1' and
                  (alg!='etpf' or float(r['epsilon'])==1)],key=lambda r:int(r['n']))
        axes[0].plot([int(r['n']) for r in p],[float(r['rmse']) for r in p],marker='o',markersize=3,
            color=COLORS[alg],linestyle=LINESTYLES[alg],label=LABELS[alg])
    axes[0].set(xlabel=r'$N$',ylabel=r'$\mathrm{RMSE}\downarrow$',title=r'(a) $m=1,\ \varepsilon=1$')
    axes[0].set_xticks([100,250,500])
    for n,color,marker in zip([100,250,500],['#475569','#0284c7','#ea580c'],['o','s','^']):
        p=sorted([r for r in accuracy if r['algorithm']=='etpf' and r['interval']=='1' and int(r['n'])==n],key=lambda r:float(r['epsilon']))
        axes[1].plot([float(r['epsilon']) for r in p],[float(r['rmse']) for r in p],marker=marker,markersize=3,
                     color=color,label=r'$N=%d$'%n)
    axes[1].set(xscale='log',xlabel=r'$\varepsilon$',title=r'(b) $m=1$')
    for alg in LABELS:
        p=sorted([r for r in timing if r['algorithm']==alg],key=lambda r:int(r['n']))
        if alg=='ekf':
            axes[2].axhline(float(p[0]['step_us_mean']),color=COLORS[alg],label='EKF')
        else:
            axes[2].plot([int(r['n']) for r in p],[float(r['step_us_mean']) for r in p],marker='o',markersize=3,
                         color=COLORS[alg],linestyle=LINESTYLES[alg],label=LABELS[alg])
    axes[2].set(yscale='log',xlabel=r'$N$',ylabel=r'每步耗时 / $\mathrm{\mu s}$',title=r'(c) 串行，$m=1$')
    axes[2].set_xticks([100,250,500])
    export(fig,'ablation_runtime',rect=legends_below(fig,axes))
    return metadata
