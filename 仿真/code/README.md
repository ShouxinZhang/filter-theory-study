# C++ 滤波仿真

环境, 算法, 冻结数据, 数值参考与评估分别实现, 数学规范见 [docs](../docs/README.md)。
需要 C++20, CMake, Eigen3 与 OpenSSL; 已复用本机依赖, 不需要 Python 环境。
Ubuntu 缺少依赖时安装 `build-essential cmake ninja-build libeigen3-dev libssl-dev`。
在本目录执行:
```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build -j 4
ctest --test-dir build --output-on-failure
build/filter_bench generate --env gordon --out data/gordon --trajectories 2
build/filter_bench run --data data/gordon --out runs/bpf --algorithm bpf
build/filter_bench run --data data/gordon --out runs/etpf --algorithm etpf
build/filter_bench evaluate --data data/gordon --runs runs/bpf --out runs/bpf-report
build/filter_bench evaluate --data data/gordon --runs runs/etpf --out runs/etpf-report
```
示例用 2 条轨迹快速运行; 正式默认是 100 条, 一维 500 粒子, 追踪 4000 粒子。
支持 Gordon 一维与原式 `atan(y/x)` 纯方位追踪, 默认正态噪声, 可配置均匀/正态分布及逐维参数。
BPF 使用多项式重采样; ETPF 一维使用单调输运, 多维使用无正则网络单纯形。
四维 ETPF 的 4000 粒子输运较耗时, 可先用 `--particles 100` 检查流程。
- [命令与续跑](docs/使用.md)
- [噪声接口与配置](docs/噪声.md)
- [模块与接口](docs/结构.md)
- [评估文件与参考精度](docs/结果.md)
- [实现地图](PLAN.md) 与 [实施记录](logs/实现记录.md)
