"""串行重测每步观测配置，固定CPU，同种子三次重复，保留可恢复记录。"""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent/'Gordon基准'
sys.path.insert(0,str(BASE/'scripts'))
from pipeline.common import atomic_json, command, digest_file
from pipeline.environment import collect, plotting_python
RUN = BASE/'runs'/(BASE/'runs/LATEST').read_text().strip()
OUT = ROOT/'data/timing'
OUT.mkdir(parents=True,exist_ok=True)
config=json.loads((RUN/'config.json').read_text())
dataset=json.loads((RUN/'dataset.json').read_text())
metadata=json.loads((RUN/'metadata.json').read_text())
# 原滤波二进制必须完全一致，避免把实现变更误当作计时变化。
assert digest_file(BASE/'build/filter') == metadata['environment']['executables']['filter']
cpu=min(os.sched_getaffinity(0))
atomic_json(OUT/'environment.json', {**collect(1,plotting_python()),'pinned_cpu':cpu,'repetitions':3,
    'timing_definition':'每条轨迹对3次重复取内核每步时间中位数，再报告8条轨迹的均值和样本标准差'})
trials={t['trial']:t for t in dataset['trials']}
jobs=[j for j in json.loads((RUN/'jobs.json').read_text()) if j['configuration']['interval']==1 and
      (j['configuration']['algorithm']!='etpf' or float(j['configuration']['epsilon'])==1)]
index=[]
for j in sorted(jobs,key=lambda j:(j['configuration']['config_id'],j['trial'])):
    cfg=j['configuration']; trial=trials[j['trial']]
    observation=Path(dataset['directory'])/trial['observations']
    assert digest_file(observation)==trial['observations_sha256']
    original=RUN/'jobs'/cfg['config_id']/('trial_%04d'%j['trial'])/'filter.csv'
    assert digest_file(original)==j['outputs']['filter.csv']
    with original.open() as f: original_rows=list(csv.DictReader(f))
    for repeat in range(3):
        folder=OUT/cfg['config_id']/('trial_%04d'%j['trial'])/('repeat_%d'%repeat)
        folder.mkdir(parents=True,exist_ok=True)
        output=folder/'filter.csv'; status=folder/'status.json'
        if not (status.exists() and output.exists() and json.loads(status.read_text()).get('sha256')==digest_file(output)):
            args=command(BASE/'build/filter', model='gordon', algorithm=cfg['algorithm'], observations=observation,
                         output=output, n=max(2,cfg['n']), epsilon=cfg['epsilon'] or 1, interval=1,
                         seed=j['algorithm_seed'], tolerance=config['solver']['tolerance'], max_iterations=config['solver']['max_iterations'])
            subprocess.run(['taskset','-c',str(cpu)]+args,check=True)
            with output.open() as f: actual=list(csv.DictReader(f))
            assert len(actual)==len(original_rows)
            for a,b in zip(actual,original_rows):
                assert all(a[k]==b[k] for k in a if k not in ('predict_us','update_us'))
            atomic_json(status,{'sha256':digest_file(output),'original_sha256':j['outputs']['filter.csv'],
                                'seed':j['algorithm_seed'],'cpu':cpu,'binary':digest_file(BASE/'build/filter')})
        index.append([cfg['config_id'],cfg['algorithm'],cfg['n'],j['trial'],repeat,str(output)])
    if j['trial']==max(trials): print(cfg['config_id'],'串行计时完成',flush=True)
with (OUT/'index.csv').open('w',newline='') as f:
    writer=csv.writer(f,lineterminator='\n');writer.writerow(['config_id','algorithm','n','trial','repeat','filter_path']);writer.writerows(index)
