#pragma once
#include "pf/core.hpp"
#include <memory>

namespace pf {
// 模型接口只公开概率模型; 固定真实初值由 benchmark 单独保存。
class Environment {
 public:
  virtual ~Environment() = default;
  virtual std::string name() const = 0;
  virtual int dimension() const = 0;
  virtual int steps() const = 0;
  virtual int initial_time() const = 0;
  virtual void sample_initial(Out x, Random& rng) const = 0;
  virtual void propagate(int k, In previous, Out next, Random& rng) const = 0;
  virtual double observe(In x, Random& rng) const = 0;
  virtual double log_likelihood(double y, In x) const = 0;
  virtual std::string parameters() const = 0;
};
std::unique_ptr<Environment> make_environment(const std::string& name);
std::unique_ptr<Environment> make_tracking();
double gordon_drift(int k, double x);
double tracking_bearing(In x);
} // namespace pf
