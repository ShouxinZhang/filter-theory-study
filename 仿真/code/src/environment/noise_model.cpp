#include "pf/environment.hpp"

namespace pf {
Environment::Environment(Noise process,Noise observation,const EnvironmentNoise& config)
    :process_(config.process.value_or(process)),observation_(config.observation.value_or(observation)),
     default_process_(process.encode()),default_observation_(observation.encode()) {
  require(process_.dimension()==process.dimension(),"过程噪声 dim 与环境入口不匹配");
  require(observation_.dimension()==observation.dimension(),"观测噪声 dim 与环境入口不匹配");
  require(observation_.dimension()==1,"当前 Environment 使用标量观测接口; 多维观测须先扩展该接口");
}
void Environment::propagate(int k,In previous,Out next,Random& rng) const {
  Vector noise(process_.dimension());process_.sample(noise,rng);transition(k,previous,noise,next);
}
double Environment::observe(In x,Random& rng) const {
  return measurement(x)+observation_.sample_component(0,rng);
}
double Environment::log_likelihood(double y,In x) const {
  // 加性观测的残差服从所配置的观测噪声, 不再硬编码高斯似然。
  return observation_.log_density_scalar(y-measurement(x));
}
std::string Environment::with_noise_parameters(const std::string& original) const {
  const auto p=process_.encode(),o=observation_.encode();
  if(p==default_process_&&o==default_observation_)return original;
  return original+"|noise-v1|"+p+"|"+o;
}
} // namespace pf
