#include "pf/transport.hpp"
#include <climits>
#include "network_simplex_simple.h"

namespace pf {
TransportPlan network_transport(const Matrix& x, In w, const TransportConfig& config) {
  validate_transport_input(x,w,config);
  // 适配固定版本 POT 的 double 网络单纯形, 完全不加入熵正则项。
  using Graph=lemon::FullBipartiteDigraph;
  using Solver=lemon::NetworkSimplexSimple<Graph,double,double,unsigned int>;
  std::vector<Eigen::Index> active;
  for (Eigen::Index i=0;i<w.size();++i) if (w[i]>0) active.push_back(i);
  const auto rows=active.size(), cols=static_cast<std::size_t>(w.size());
  require(rows+cols < INT_MAX && rows*cols < INT_MAX, "输运规模超出求解器索引范围");
  Graph graph(rows,cols);
  Solver solver(graph,true,static_cast<int>(rows+cols),rows*cols,config.max_iterations);
  std::vector<double> supply(rows), demand(cols,-1.0/cols);
  for (std::size_t i=0;i<rows;++i) supply[i]=w[active[i]];
  solver.supplyMap(supply.data(),static_cast<int>(rows),demand.data(),static_cast<int>(cols));
  for (std::size_t i=0;i<rows;++i)
    for (std::size_t j=0;j<cols;++j)
      solver.setCost(graph.arcFromId(i*cols+j),(x.col(active[i])-x.col(j)).squaredNorm());
  const auto status=solver.run();
  require(status==Solver::OPTIMAL, "无正则输运求解未收敛, 状态="+std::to_string(status));
  TransportPlan plan;
  plan.masses.reserve(rows+cols);
  double dual=0;
  // 从对偶势构造可行下界, 向下校正浮点约束违背, 独立核查最优性。
  for (std::size_t i=0;i<rows;++i) {
    double alpha=-solver.potential(static_cast<int>(i));
    for (std::size_t j=0;j<cols;++j) {
      const double cost=(x.col(active[i])-x.col(j)).squaredNorm();
      alpha=std::min(alpha,cost-solver.potential(static_cast<int>(rows+j)));
      const double mass=solver.flow(graph.arcFromId(i*cols+j));
      if (mass!=0) plan.masses.push_back({active[i],static_cast<Eigen::Index>(j),mass});
      plan.diagnostics.objective+=mass*cost;
    }
    dual+=w[active[i]]*alpha;
  }
  for (std::size_t j=0;j<cols;++j) dual+=solver.potential(static_cast<int>(rows+j))/cols;
  plan.diagnostics.dual_gap=plan.diagnostics.objective-dual;
  check_marginals(plan,w,config);
  return plan;
}
} // namespace pf
