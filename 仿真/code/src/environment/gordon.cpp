#include "pf/environment.hpp"
#include <cmath>

namespace pf {
double gordon_drift(int k, double x) {
  return 0.5*x + 25*x/(1+x*x) + 8*std::cos(1.2*(k-1));
}
class Gordon final : public Environment {
 public:
  explicit Gordon(const EnvironmentNoise& config)
      :Environment(Noise::normal(1,0,std::sqrt(10.0)),Noise::normal(1),config) {}
  std::string name() const override { return "gordon-v1"; }
  int dimension() const override { return 1; }
  int steps() const override { return 50; }
  int initial_time() const override { return 0; }
  void sample_initial(Out x, Random& rng) const override { x[0] = std::sqrt(2.0)*rng.normal(); }
  void transition(int k,In x,In noise,Out next) const override {
    require(k>=1&&x.size()==1&&next.size()==1&&noise.size()==1,"一维状态转移的时刻或维度错误");
    next[0] = gordon_drift(k, x[0]) + noise[0];
  }
  double measurement(In x) const override { require(x.size()==1,"一维观测状态维度错误");return x[0]*x[0]/20; }
  std::string parameters() const override {
    return with_noise_parameters("q=10;r=1;prior_mean=0;prior_variance=2;K=50;initial_time=0;phase=1.2*(k-1)");
  }
};
std::unique_ptr<Environment> make_gordon(const EnvironmentNoise& config) { return std::make_unique<Gordon>(config); }
} // namespace pf
