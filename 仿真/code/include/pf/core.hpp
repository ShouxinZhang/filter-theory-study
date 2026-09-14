#pragma once
#include <Eigen/Core>
#include <cstdint>
#include <random>
#include <string>
#include <vector>

namespace pf {
using Vector = Eigen::VectorXd;
using Matrix = Eigen::MatrixXd; // 列对应粒子, 与数学文档 X_k^{±} 一致。
using In = Eigen::Ref<const Vector>;
using Out = Eigen::Ref<Vector>;

// 固定 mt19937_64 + Box-Muller-v1, 不依赖各标准库的 normal_distribution。
class Random {
 public:
  explicit Random(std::uint64_t seed) : engine_(seed) {}
  double uniform();
  double normal();
 private:
  std::mt19937_64 engine_;
  bool spare_ready_ = false;
  double spare_ = 0;
};
std::uint64_t seed_for(std::uint64_t base, std::uint64_t trajectory, std::uint64_t stream);
Vector normalized_log_weights(In log_weights);
Matrix covariance(const Matrix& particles, In weights, In mean);
void require(bool condition, const std::string& message);
} // namespace pf
