#pragma once
#include "pf/environment.hpp"
#include "pf/records.hpp"

namespace pf {
Matrix multinomial_resample(const Matrix& x, In weights, Random& rng);
// 实例只保存模型与自身粒子, 类型上不接受 Dataset 或 Truth。
class ParticleFilter {
 public:
  ParticleFilter(const Environment& model, FilterConfig config, int trajectory);
  FilterStep step(int k, double observation);
 private:
  const Environment& model_;
  FilterConfig config_;
  Random initialization_, propagation_, resampling_;
  Matrix posterior_;
  int next_k_=1;
  bool failed_=false;
};
} // namespace pf
