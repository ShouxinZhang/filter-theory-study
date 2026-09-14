#include "pf/transport.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>

namespace pf {
void validate_transport_input(const Matrix& x, In w, const TransportConfig& config) {
  require(x.cols() > 0 && x.rows() > 0 && w.size() == x.cols(), "输运输入维度错误");
  require(x.allFinite() && w.allFinite() && w.minCoeff() >= 0, "输运输入必须有限且权重非负");
  require(std::isfinite(config.tolerance) && config.tolerance > 0 && config.tolerance <= 1e-4,
          "输运容差必须在 (0,1e-4] 内");
  require(config.max_iterations > 0, "输运迭代上限必须为正");
  require(std::abs(w.sum()-1) <= 1e-12, "输运权重和必须为 1");
}
void check_marginals(TransportPlan& plan, In w, const TransportConfig& config) {
  Vector row = Vector::Zero(w.size()), col = row;
  for (const auto& mass : plan.masses) {
    require(std::isfinite(mass.value), "输运质量非有限");
    row[mass.source] += mass.value; col[mass.target] += mass.value;
    plan.diagnostics.negative_mass = std::max(plan.diagnostics.negative_mass, -mass.value);
  }
  auto& d = plan.diagnostics;
  d.marginal_residual = std::max((row-w).cwiseAbs().maxCoeff(),
                                (col.array()-1.0/w.size()).abs().maxCoeff());
  require(d.marginal_residual <= config.tolerance && d.negative_mass <= config.tolerance,
          "输运解违反边际或非负约束");
  require(std::isfinite(d.objective) && std::isfinite(d.dual_gap) &&
          std::abs(d.dual_gap) <= config.tolerance*std::max(1.0, std::abs(d.objective)),
          "输运解未达到最优性容差");
}
TransportPlan monotone_transport(const Matrix& x, In w, const TransportConfig& config) {
  validate_transport_input(x, w, config);
  require(x.rows() == 1, "单调输运只适用于一维");
  std::vector<Eigen::Index> order(static_cast<std::size_t>(w.size()));
  std::iota(order.begin(), order.end(), 0);
  std::stable_sort(order.begin(), order.end(), [&](auto i, auto j) { return x(0,i)<x(0,j); });
  TransportPlan plan;
  plan.masses.reserve(2*order.size());
  std::size_t i=0, j=0;
  double source_left=w[order[0]], target_left=1.0/w.size();
  // 两个排序 CDF 的区间重叠就是一维平方代价的全局最优耦合。
  while (i<order.size() && j<order.size()) {
    const double mass=std::min(source_left,target_left);
    if (mass>0) {
      plan.masses.push_back({order[i],order[j],mass});
      const double delta=x(0,order[i])-x(0,order[j]);
      plan.diagnostics.objective += mass*delta*delta;
    }
    source_left-=mass; target_left-=mass;
    if (source_left<=0) { if (++i<order.size()) source_left=w[order[i]]; }
    if (target_left<=0) { ++j; target_left=1.0/w.size(); }
  }
  check_marginals(plan,w,config);
  return plan;
}
} // namespace pf
