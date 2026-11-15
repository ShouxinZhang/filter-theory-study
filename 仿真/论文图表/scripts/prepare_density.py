"""复用冻结运行绘制四算法后验；C++完成粒子递推与核密度计算。"""
import csv
import json
from pathlib import Path
import subprocess
import sys
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent/'Gordon基准'
sys.path.insert(0,str(BASE/'scripts'))
from pipeline.common import atomic_json, command, digest_file
from plot_style import style, save
RUN=BASE/'runs'/(BASE/'runs/LATEST').read_text().strip();OUT=ROOT/'data/kde';FIG=ROOT/'figures'
STEPS=(11,21)
CONFIGS={'bpf':'bpf_n500_e0_m1','enkf':'enkf_n500_e0_m1','etpf':'etpf_n500_e1_m1','ekf':'ekf_n0_e0_m1'}
STAGES={'bpf':'系统重采样后的等权粒子','enkf':'观测更新后的集合','etpf':'输运后的等权粒子'}
CURVES={'bpf':('#245a81','-'),'enkf':('#cf8531','-.'),'etpf':('#258679',(0,(3,1,1,1)))}

def read(path):
    with Path(path).open() as stream:return list(csv.DictReader(stream))

def snapshot(step,algorithm,job,observation,paths):
    """恢复同一随机流，逐字段检查快照前缀，排除计时字段。"""
    folder=OUT/('k%d'%step)/algorithm
    subprocess.run(command(BASE/'build/posterior_snapshot',observations=observation,step=step,n=500,
        algorithm=algorithm,epsilon=1,tolerance=1e-8,max_iterations=1000,
        seed=job['algorithm_seed'],output=folder),check=True)
    actual=read(folder/'filter.csv');original=read(paths[algorithm])
    if len(actual)!=step or len(original)<step:raise RuntimeError('粒子导出时间长度不匹配')
    for a,b in zip(actual,original):
        if any(a[key]!=b[key] for key in a if key not in ('predict_us','update_us')):
            raise RuntimeError(f'{algorithm}在第{a["step"]}步与冻结运行不一致')
    subprocess.run(command(BASE/'build/kde_density',particles=folder/'particles.csv',ekf=paths['ekf'],step=step,output=folder),check=True)
    return {'algorithm':algorithm,'particle_stage':STAGES[algorithm],**read(folder/'metadata.csv')[0]}

def plot(truth):
    """各集合独立选Scott带宽；曲线展示更新后的分布而非点估计。"""
    font=style();plt.rcParams.update({'font.size':8,'axes.labelsize':8,'axes.titlesize':9,'legend.fontsize':7,
                                    'xtick.labelsize':7,'ytick.labelsize':7,'pdf.fonttype':42})
    fig,axes=plt.subplots(1,2,figsize=(5.5,1.6))
    for ax,step in zip(axes,STEPS):
        for algorithm,(color,line) in CURVES.items():
            rows=read(OUT/('k%d'%step)/algorithm/'density.csv');x=[float(r['x']) for r in rows]
            ax.plot(x,[float(r['kde']) for r in rows],color=color,linestyle=line,linewidth=1.25,
                    label={'bpf':'BPF','enkf':'EnKF','etpf':'ETPF'}[algorithm])
        ax.plot(x,[float(r['ekf_gaussian']) for r in rows],color='#ba2626',linestyle='--',linewidth=1.15,label='EKF（高斯）')
        ax.axvline(truth[step],color='#444444',linestyle=':',linewidth=1,label='真值')
        ax.set(title=r'$k=%d$'%step,xlabel=r'$x_k$',ylabel=r'$\widehat p(x_k\mid y_{1:k})$')
        ax.set_ylim(bottom=0)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(0.5,1.05),ncol=5,frameon=False)
    save(fig,FIG,'posterior_density.png',rect=(0,0,1,.96))
    fig.savefig(FIG/'posterior_density.pdf',bbox_inches='tight')
    return font

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    dataset=json.loads((RUN/'dataset.json').read_text());trial=dataset['trials'][0]
    observation=Path(dataset['directory'])/trial['observations'];truth_path=Path(dataset['directory'])/trial['truth']
    for field,path in [('observations',observation),('truth',truth_path)]:
        if digest_file(path)!=trial[field+'_sha256']:raise RuntimeError('冻结数据哈希不匹配')
    jobs=json.loads((RUN/'jobs.json').read_text());selected={};paths={}
    for name,config in CONFIGS.items():
        selected[name]=next(j for j in jobs if j['configuration']['config_id']==config and j['trial']==trial['trial'])
        paths[name]=RUN/'jobs'/config/('trial_%04d'%trial['trial'])/'filter.csv'
        if digest_file(paths[name])!=selected[name]['outputs']['filter.csv']:raise RuntimeError('原始滤波输出哈希不匹配')
    truth={int(r['step']):float(r['x']) for r in read(truth_path)}
    diagnostics=[{**snapshot(step,algorithm,selected[algorithm],observation,paths),'truth':truth[step]}
                 for step in STEPS for algorithm in CURVES]
    font=plot(truth)
    atomic_json(OUT/'provenance.json',{'dataset':dataset['dataset_id'],'trial':trial['trial'],'steps':STEPS,'n':500,'interval':1,
        'epsilon':1,'sinkhorn_tolerance':1e-8,'sinkhorn_max_iterations':1000,
        'algorithm_seeds':{a:j['algorithm_seed'] for a,j in selected.items()},
        'bandwidth_rule':'各集合样本标准差乘N^(-1/5)，Scott规则','diagnostics':diagnostics,'font':font,
        'method_reference':'https://docs.scipy.org/doc/scipy-1.14.1/reference/generated/scipy.stats.gaussian_kde.html',
        'inputs':{str(p):digest_file(p) for p in [observation,truth_path,*paths.values()]},
        'source':{str(p.relative_to(BASE)):digest_file(p) for p in [BASE/'apps/posterior_snapshot.cpp',BASE/'apps/kde_density.cpp',
            BASE/'src/evaluation/density.cpp',BASE/'include/baseline/density.hpp',BASE/'build/posterior_snapshot',BASE/'build/kde_density']},
        'plot_script_sha256':digest_file(Path(__file__))})
    # 清理初版单算法的派生文件，保留按算法分目录的数据与原稿备份。
    for step in STEPS:
        for filename in ('particles.csv','filter.csv','density.csv','metadata.csv'):
            (OUT/('k%d'%step)/filename).unlink(missing_ok=True)
    print(json.dumps(diagnostics,ensure_ascii=False))

if __name__=='__main__':prepare()
