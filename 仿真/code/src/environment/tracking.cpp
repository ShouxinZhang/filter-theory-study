#include "pf/environment.hpp"
#include <cmath>
#include <numbers>

namespace pf {
double tracking_bearing(In x) {
  // 保留原论文 atan(y/x) 主值及前后向模糊性, 不能替换成 atan2。
  if (x[0] == 0) return x[2] == 0 ? 0 : std::copysign(std::numbers::pi/2, x[2]);
  return std::atan(x[2]/x[0]);
}
class Tracking final : public Environment {
 public:
  std::string name() const override { return "tracking-v1"; }
  int dimension() const override { return 4; }
  int steps() const override { return 24; }
  int initial_time() const override { return 1; }
  void sample_initial(Out x, Random& rng) const override {
    x[0] = 0.5*rng.normal(); x[1] = 0.005*rng.normal();
    x[2] = 0.4 + 0.3*rng.normal(); x[3] = -0.05 + 0.01*rng.normal();
  }
  void propagate(int k, In x, Out next, Random& rng) const override {
    require(k >= 2, "追踪环境首步必须直接观测更新");
    const double ax = 0.001*rng.normal(), ay = 0.001*rng.normal();
    next[0] = x[0]+x[1]+0.5*ax; next[1] = x[1]+ax;
    next[2] = x[2]+x[3]+0.5*ay; next[3] = x[3]+ay;
  }
  double observe(In x, Random& rng) const override { return tracking_bearing(x)+0.005*rng.normal(); }
  double log_likelihood(double y, In x) const override {
    const double residual = (y-tracking_bearing(x))/0.005;
    return -0.5*residual*residual - std::log(0.005*std::sqrt(2*std::numbers::pi));
  }
  std::string parameters() const override {
    return "q=1e-6;r=2.5e-5;dt=1;prior_mean=0,0,0.4,-0.05;prior_sd=0.5,0.005,0.3,0.01;K=24;initial_time=1;angle=atan(y/x)";
  }
};
std::unique_ptr<Environment> make_tracking() { return std::make_unique<Tracking>(); }
} // namespace pf
