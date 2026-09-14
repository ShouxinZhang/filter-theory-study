#pragma once
#include "pf/noise.hpp"
#include <memory>

namespace pf {
// 模型接口只公开概率模型; 固定真实初值由 benchmark 单独保存。
class Environment {
 public:
  Environment(Noise default_process,Noise default_observation,const EnvironmentNoise& config);
  virtual ~Environment() = default;
  virtual std::string name() const = 0;
  virtual int dimension() const = 0;
  virtual int steps() const = 0;
  virtual int initial_time() const = 0;
  virtual void sample_initial(Out x, Random& rng) const = 0;
  virtual void transition(int k,In previous,In noise,Out next) const = 0;
  virtual double measurement(In x) const = 0;
  void propagate(int k,In previous,Out next,Random& rng) const;
  double observe(In x,Random& rng) const;
  double log_likelihood(double y,In x) const;
  const Noise& process_noise() const { return process_; }
  const Noise& observation_noise() const { return observation_; }
  virtual std::string parameters() const = 0;
 protected:
  std::string with_noise_parameters(const std::string& original) const;
 private:
  Noise process_,observation_;
  std::string default_process_,default_observation_;
};
std::unique_ptr<Environment> make_environment(const std::string& name,const EnvironmentNoise& config={});
std::unique_ptr<Environment> environment_from_parameters(const std::string& name,const std::string& parameters);
std::unique_ptr<Environment> make_gordon(const EnvironmentNoise& config);
std::unique_ptr<Environment> make_tracking(const EnvironmentNoise& config);
double gordon_drift(int k, double x);
double tracking_bearing(In x);
} // namespace pf
