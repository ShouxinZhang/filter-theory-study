#include "options.hpp"
#include "pf/environment.hpp"
#include <sstream>

namespace app {
// 单个数广播, 逗号分隔的列表逐维配置; 不接受缺项或静默截断。
static pf::Vector parameter(const Options& o,const std::string& key,int dim,const pf::Vector& fallback) {
  if(!o.flag(key)) {
    if(fallback.size()==dim)return fallback;
    return pf::Vector::Constant(dim,fallback[0]);
  }
  const auto text=o.get(key);pf::require(!text.empty()&&text.back()!=',',"噪声参数列表不能为空: "+key);
  std::istringstream input(text);std::string token;std::vector<double> values;
  while(std::getline(input,token,',')) {
    std::size_t used=0;double value=std::stod(token,&used);
    pf::require(used==token.size()&&std::isfinite(value),"噪声参数不是有限数字: "+key);
    values.push_back(value);
  }
  pf::require(values.size()==1||values.size()==static_cast<std::size_t>(dim),"噪声参数项数必须为 1 或 dim: "+key);
  pf::Vector result(dim);
  for(int j=0;j<dim;++j)result[j]=values.size()==1?values[0]:values[j];
  return result;
}
static pf::Noise configured(const Options& o,const std::string& prefix,const pf::Noise& base) {
  const auto kind=o.get(prefix+"-noise",base.kind()==pf::NoiseKind::normal?"normal":"uniform");
  const int dim=o.integer(prefix+"-dim",base.dimension());
  pf::require(dim>0&&dim<=1000000,"噪声 dim 必须在 1 到 1000000 之间");
  if(kind=="normal") {
    pf::require(!o.flag(prefix+"-lower")&&!o.flag(prefix+"-upper"),"正态噪声不接受 lower/upper");
    const auto mean=parameter(o,prefix+"-mean",dim,base.kind()==pf::NoiseKind::normal?base.first():pf::Vector::Zero(1));
    const auto sd=parameter(o,prefix+"-std",dim,base.kind()==pf::NoiseKind::normal?base.second():pf::Vector::Ones(1));
    return pf::Noise::normal(mean,sd);
  }
  pf::require(kind=="uniform","噪声类别只能是 normal 或 uniform");
  pf::require(!o.flag(prefix+"-mean")&&!o.flag(prefix+"-std"),"均匀噪声不接受 mean/std");
  return pf::Noise::uniform(parameter(o,prefix+"-lower",dim,pf::Vector::Constant(1,-1)),
                            parameter(o,prefix+"-upper",dim,pf::Vector::Ones(1)));
}
pf::EnvironmentNoise noise_options(const Options& o,const std::string& environment) {
  auto model=pf::make_environment(environment);
  return {configured(o,"process",model->process_noise()),configured(o,"observation",model->observation_noise())};
}
} // namespace app
