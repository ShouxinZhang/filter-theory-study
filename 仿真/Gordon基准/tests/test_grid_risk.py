"""手算两条轨迹，校验独立评价与轨迹级 delta-method 置信区间。"""
import csv
import math
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
HEADER = 'step,observed,prior_mean,prior_var,prior_low,prior_high,post_mean,post_var,post_low,post_high,predict_us,update_us,ess,sinkhorn_iterations,sinkhorn_residual,sinkhorn_converged,rounding_l1,transport_cost\n'
with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    lines = ['truth_path,filter_path']
    for i, value in enumerate((1, 2)):
        truth, output = folder / f'truth{i}.csv', folder / f'filter{i}.csv'
        truth.write_text(f'step,x\n1,{value}\n')
        output.write_text(HEADER + f'1,1,0,{value**2},-5,5,0,{value**2},-5,5,0,0,nan,0,nan,-1,nan,nan\n')
        lines.append(f'{truth},{output}')
    index = folder / 'index.csv'; index.write_text('\n'.join(lines)+'\n')
    risk = folder / 'risk.csv'
    subprocess.run([str(ROOT/'build/grid_risk'),'--index',str(index),'--output',str(risk)],check=True)
    with risk.open() as f: total=list(csv.DictReader(f))[-1]
    with Path(str(risk)+'.ci.csv').open() as f: ci=list(csv.DictReader(f))[0]
    assert math.isclose(float(total['rmse']),math.sqrt(2.5),rel_tol=1e-12)
    assert float(total['nrmse']) == float(ci['relative_risk']) == 1
    assert float(ci['relative_se']) == 0
    assert math.isclose(float(ci['risk_root_se']),1.5/(2*math.sqrt(2.5)),rel_tol=1e-12)
print('独立风险评价手算校验通过')
