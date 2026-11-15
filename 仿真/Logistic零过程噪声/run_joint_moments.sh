#!/usr/bin/env bash
set -euo pipefail
task_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g++ -std=c++20 -O3 -fopenmp -Wall -Wextra -Wpedantic -I "$task_dir/../code/include" -I /usr/include/eigen3 \
  "$task_dir/joint_moments.cpp" -L "$task_dir/build" -lfilters -lenvironments -ltransport -lnoise -lfilter_core \
  -o "$task_dir/joint_moments"
OMP_NUM_THREADS=4 "$task_dir/joint_moments" "$task_dir/runs"
