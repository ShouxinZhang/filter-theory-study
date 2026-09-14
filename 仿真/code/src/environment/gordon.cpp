#include "pf/environment.hpp"
#include <cmath>
#include <numbers>

namespace pf {
double gordon_drift(int k, double x) {
  return 0.5*x + 25*x/(1+x*x) + 8*std::cos(1.2*(k-1));
}
class Gordon final : public Environment {
 public:
  std::string name() const override { return "gordon-v1"; }
  int dimension() const override { return 1; }
  int steps() const override { return 50; }
  int initial_time() const override { return 0; }
  void sample_initial(Out x, Random& rng) const override { x[0] = std::sqrt(2.0)*rng.normal(); }
  void propagate(int k, In x, Out next, Random& rng) const override {
    next[0] = gordon_drift(k, x[0]) + std::sqrt(10.0)*rng.normal();
  }
  double observe(In x, Random& rng) const override { return x[0]*x[0]/20 + rng.normal(); }
  double log_likelihood(double y, In x) const override {
    const double residual = y - x[0]*x[0]/20;
    return -0.5*(residual*residual + std::log(2*std::numbers::pi));
  }
  std::string parameters() const override {
    return "q=10;r=1;prior_mean=0;prior_variance=2;K=50;initial_time=0;phase=1.2*(k-1)";
  }
};
std::unique_ptr<Environment> make_environment(const std::string& name) {
  if (name == "gordon" || name == "gordon-v1") return std::make_unique<Gordon>();
  if (name == "tracking" || name == "tracking-v1") return make_tracking();
  throw std::runtime_error("未知环境: " + name);
}
} // namespace pf
