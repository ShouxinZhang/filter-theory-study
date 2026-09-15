"""Analytic Gaussian illustration, not measured filtering performance.
Reproduce: uv run --with numpy --with matplotlib python research/make_figure.py
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
x = np.linspace(-3, 3, 601)
def density(mean, variance):
    return np.exp(-(x-mean)**2/(2*variance))/np.sqrt(2*np.pi*variance)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 13, 'svg.fonttype': 'none'})
fig, ax = plt.subplots(figsize=(7.4, 4.1), constrained_layout=True)
ax.plot(x, density(0, 1), label='Prior', color='#738395', linewidth=2.4, linestyle='--')
ax.plot(x, density(.8, .2), label='Posterior', color='#165a72', linewidth=2.8)
ax.set(xlabel='State x', ylabel='Density', xlim=(-3, 3), ylim=(0, 1.02))
ax.spines[['top', 'right']].set_visible(False)
ax.legend(frameon=False, loc='upper left')
ax.grid(axis='y', alpha=.18)
out = Path(__file__).resolve().parents[1]/'talks/starter/public/gaussian-update.svg'
fig.savefig(out)
print(out)
