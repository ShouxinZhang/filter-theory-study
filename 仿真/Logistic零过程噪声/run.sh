#!/usr/bin/env bash
set -euo pipefail
task_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_dir="$(cd -- "$task_dir/../code" && pwd)"
build_dir="$task_dir/build"
cmake -S "$source_dir" -B "$build_dir" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
cmake --build "$build_dir" --target filters -j 4
g++ -std=c++20 -O3 -fopenmp -Wall -Wextra -Wpedantic -I "$source_dir/include" -I /usr/include/eigen3 \
  "$task_dir/experiment.cpp" -L "$build_dir" -lfilters -lenvironments -ltransport -lnoise -lfilter_core -o "$task_dir/experiment"
"$task_dir/experiment" generate "$task_dir/runs" reflect
g++ -std=c++17 -O3 -fopenmp -Wall -Wextra -Wpedantic "$task_dir/reference.cpp" -o "$task_dir/reference"
OMP_NUM_THREADS=4 "$task_dir/reference" "$task_dir/runs/data.csv" "$task_dir/runs/reference_8192.bin" 64 1000 8192 .1
OMP_NUM_THREADS=4 "$task_dir/reference" "$task_dir/runs/data.csv" "$task_dir/runs/reference_16384.bin" 64 1000 16384 .1
OMP_NUM_THREADS=4 "$task_dir/experiment" calculate "$task_dir/runs" reflect
