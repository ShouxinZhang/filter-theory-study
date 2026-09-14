#pragma once
#include "pf/core.hpp"
#include <optional>

namespace pf {
enum class NoiseKind { normal, uniform };

// 不可变的逐维独立分布; 随机状态由调用者持有, 可安全跨轨迹线程共享。
class Noise {
 public:
  static Noise normal(int dim,double mean=0,double stddev=1);
  static Noise normal(Vector mean,Vector stddev);
  static Noise uniform(int dim,double lower=-1,double upper=1);
  static Noise uniform(Vector lower,Vector upper);
  static Noise decode(const std::string& description);
  std::string encode() const;
  int dimension() const { return static_cast<int>(first_.size()); }
  NoiseKind kind() const { return kind_; }
  const Vector& first() const { return first_; }   // 正态均值或均匀下界。
  const Vector& second() const { return second_; } // 正态标准差或均匀上界。
  void sample(Out output,Random& rng) const;
  double sample_component(int j,Random& rng) const;
  double log_density(In value) const;
  double log_density_scalar(double value) const;
  void log_density_scalar_batch(In values,Out output) const; // 一维分布的批量积分核。
 private:
  Noise(NoiseKind kind,Vector first,Vector second);
  double component_log_density(int j,double value) const;
  NoiseKind kind_;
  Vector first_,second_,log_normalizer_;
};
// 未指定的入口沿用该环境的基准噪声。
struct EnvironmentNoise { std::optional<Noise> process,observation; };
} // namespace pf
