#pragma once
#include "pf/transport.hpp"

namespace pf {
struct FilterConfig {
  std::string algorithm="bpf";
  int particles=500;
  std::uint64_t seed=20260914;
  TransportConfig transport;
};
// 一步输出包含等权化前的后验与用于下一步的等权粒子, 评估无须接触算法对象。
struct FilterStep {
  int k=0;
  Vector mean, weights;
  Matrix predicted, posterior;
  TransportDiagnostics transport;
  double elapsed_ms=0;
};
struct RunRecord {
  std::string environment, variant, data_hash;
  int trajectory=0;
  FilterConfig config;
  double initialization_ms=0;
  std::vector<FilterStep> steps;
  int failure_k=0;
  std::string failure;
};
struct ReferenceStep {
  int k=0;
  Vector mean;
  Matrix covariance;
};
struct ReferenceRecord {
  std::string environment, variant, data_hash, method;
  int trajectory=0;
  bool validated=false;
  double mean_precision=0, covariance_precision=0;
  std::vector<ReferenceStep> steps;
};
} // namespace pf
