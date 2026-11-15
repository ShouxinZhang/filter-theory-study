"""实验配置：所有超参数集中于此，其他模块不得硬编码。"""
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]                      # 本实验的根目录
DATA = ROOT / "data"                                            # MNIST；缺失时自动下载
OUT = ROOT / "outputs"


@dataclass
class Config:
    # --- 模型 ---
    n_d: int = 16            # 潜空间维数
    window: int = 7          # 观测窗口边长，28/7=4，共 16 个窗口
    sigma: float = 0.3       # 观测噪声标准差
    # --- 训练 ---
    ae_epochs: int = 30      # 压缩还原算子的训练轮数
    readout_epochs: int = 15 # 类别读出的训练轮数
    amort_seconds: float = 240.0  # 摊销映射的训练时长（按墙钟限时）
    amort_inner: int = 5     # 每次更新检验函数 f 之前，映射 T 的更新次数
    batch: int = 1024
    # --- 滤波 ---
    n_particles: int = 256   # 粒子数 N
    n_test: int = 500        # 测试图像数
    eps_rel: float = 0.005   # 熵正则强度，相对于平均代价
    sinkhorn_iters: int = 50
    online_iters: int = 300  # 逐步训练方法每步的外层迭代数
    online_hidden: int = 64
    online_lr: float = 5e-4
    online_inner: int = 5    # 逐步训练方法中映射 T 的内层更新次数
    online_ypca: int = 4     # 大于 0 时，把窗口观测投影到前若干主方向后再送入网络
    jitter: float = 0.1      # 带扰动的无输运方法所加噪声标准差
    seed: int = 0

    @property
    def n_steps(self) -> int:
        return (28 // self.window) ** 2

    def to_dict(self):
        return asdict(self)
