#include "pf/environment.hpp"
#include <cmath>
#include <numbers>

namespace pf {
double tracking_bearing(In x) {
  require(x.size()==4,"追踪观测状态维度错误");
  // 保留原论文 atan(y/x) 主值及前后向模糊性, 不能替换成 atan2。
  if (x[0] == 0) return x[2] == 0 ? 0 : std::copysign(std::numbers::pi/2, x[2]);
  return std::atan(x[2]/x[0]);
}
class Tracking final : public Environment {
 public:
  explicit Tracking(const EnvironmentNoise& config)
      :Environment(Noise::normal(2,0,0.001),Noise::normal(1,0,0.005),config) {}
  std::string name() const override { return "tracking-v1"; }
  int dimension() const override { return 4; }
  int steps() const override { return 24; }
  int initial_time() const override { return 1; }
  void sample_initial(Out x, Random& rng) const override {
    x[0] = 0.5*rng.normal(); x[1] = 0.005*rng.normal();
    x[2] = 0.4 + 0.3*rng.normal(); x[3] = -0.05 + 0.01*rng.normal();
  }
  void transition(int k,In x,In noise,Out next) const override {
    require(k >= 2, "追踪环境首步必须直接观测更新");
    require(x.size()==4&&next.size()==4&&noise.size()==2,"追踪状态转移维度错误");
    const double ax=noise[0],ay=noise[1];
    next[0] = x[0]+x[1]+0.5*ax; next[1] = x[1]+ax;
    next[2] = x[2]+x[3]+0.5*ay; next[3] = x[3]+ay;
  }
  double measurement(In x) const override { return tracking_bearing(x); }
  std::string parameters() const override {
    return with_noise_parameters("q=1e-6;r=2.5e-5;dt=1;prior_mean=0,0,0.4,-0.05;prior_sd=0.5,0.005,0.3,0.01;K=24;initial_time=1;angle=atan(y/x)");
  }
};
std::unique_ptr<Environment> make_tracking(const EnvironmentNoise& config) { return std::make_unique<Tracking>(config); }
} // namespace pf
