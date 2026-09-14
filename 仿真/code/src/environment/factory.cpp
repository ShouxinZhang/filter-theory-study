#include "pf/environment.hpp"

namespace pf {
std::unique_ptr<Environment> make_environment(const std::string& name,const EnvironmentNoise& config) {
  if(name=="gordon"||name=="gordon-v1")return make_gordon(config);
  if(name=="tracking"||name=="tracking-v1")return make_tracking(config);
  throw std::runtime_error("未知环境: "+name);
}
std::unique_ptr<Environment> environment_from_parameters(const std::string& name,const std::string& parameters) {
  auto original=make_environment(name);
  if(parameters==original->parameters())return original; // 原默认数据描述继续有效。
  const auto prefix=original->parameters()+"|noise-v1|";
  require(parameters.starts_with(prefix),"冻结数据模型参数与当前实现不匹配");
  const auto split=parameters.find('|',prefix.size());
  require(split!=std::string::npos,"冻结数据缺少观测噪声配置");
  EnvironmentNoise noise;
  noise.process=Noise::decode(parameters.substr(prefix.size(),split-prefix.size()));
  noise.observation=Noise::decode(parameters.substr(split+1));
  auto model=make_environment(name,noise);
  require(model->parameters()==parameters,"冻结噪声描述不是规范格式");
  return model;
}
} // namespace pf
