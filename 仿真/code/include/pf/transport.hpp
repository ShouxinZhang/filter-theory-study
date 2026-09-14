#pragma once
#include "pf/core.hpp"

namespace pf {
struct TransportConfig {
  double tolerance = 1e-9;
  std::uint64_t max_iterations = 2000000;
};
struct TransportDiagnostics {
  double objective = 0, marginal_residual = 0, negative_mass = 0, dual_gap = 0;
};
struct Mass { Eigen::Index source, target; double value; };
struct TransportPlan {
  std::vector<Mass> masses; // 稀疏耦合, 避免把多数为零的 Pi 全部复制到输出。
  TransportDiagnostics diagnostics;
};
TransportPlan monotone_transport(const Matrix& x, In weights, const TransportConfig& config);
TransportPlan network_transport(const Matrix& x, In weights, const TransportConfig& config);
void validate_transport_input(const Matrix& x, In weights, const TransportConfig& config);
void check_marginals(TransportPlan& plan, In weights, const TransportConfig& config);
} // namespace pf
