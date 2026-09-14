#include "pf/core.hpp"
#include <cmath>
#include <stdexcept>

namespace pf {
void require(bool condition, const std::string& message) {
  if (!condition) throw std::runtime_error(message);
}
Vector normalized_log_weights(In values) {
  require(values.size() > 0, "权重不能为空");
  // -inf 允许表示零似然, 但 NaN, +inf 和全部 -inf 必须失败。
  for (double v : values) require(!std::isnan(v) && v != INFINITY, "似然非有限");
  const double maximum = values.maxCoeff();
  require(std::isfinite(maximum), "全部粒子似然为零");
  Vector weights = (values.array() - maximum).exp();
  const double sum = weights.sum();
  require(std::isfinite(sum) && sum > 0, "权重无法归一化");
  weights /= sum;
  return weights;
}
Matrix covariance(const Matrix& x, In w, In mean) {
  require(x.cols() == w.size() && x.rows() == mean.size(), "协方差维度不匹配");
  Matrix result = Matrix::Zero(x.rows(), x.rows());
  for (Eigen::Index i = 0; i < x.cols(); ++i) {
    Vector delta = x.col(i) - mean;
    result.noalias() += w[i] * delta * delta.transpose();
  }
  return result; // 后验二阶中心矩, 不使用 N-1 修正。
}
} // namespace pf
