#include "pf/filter.hpp"
#include <algorithm>
#include <numeric>

namespace pf {
Matrix multinomial_resample(const Matrix& x, In w, Random& rng) {
  require(x.cols()==w.size() && w.size()>0 && w.allFinite() && w.minCoeff()>=0 &&
          std::abs(w.sum()-1)<1e-12,"重采样权重非法");
  std::vector<double> cumulative(static_cast<std::size_t>(w.size()));
  std::partial_sum(w.begin(),w.end(),cumulative.begin());
  cumulative.back()=1; // 消除累加尾端的舍入差, 不改变中间权重。
  Matrix result(x.rows(),x.cols());
  for (Eigen::Index j=0;j<x.cols();++j) {
    const auto it=std::upper_bound(cumulative.begin(),cumulative.end(),rng.uniform());
    result.col(j)=x.col(std::distance(cumulative.begin(),it));
  }
  return result;
}
} // namespace pf
