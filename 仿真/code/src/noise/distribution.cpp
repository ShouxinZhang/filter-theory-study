#include "pf/noise.hpp"
#include <cmath>
#include <numbers>

namespace pf {
static void check_dimension(int dim) { require(dim>0 && dim<=1000000,"噪声 dim 必须在 1 到 1000000 之间"); }
Noise::Noise(NoiseKind kind,Vector first,Vector second)
    :kind_(kind),first_(std::move(first)),second_(std::move(second)) {
  check_dimension(dimension());
  require(first_.size()==second_.size(),"噪声参数数组长度必须等于 dim");
  require(first_.allFinite()&&second_.allFinite(),"噪声参数必须有限");
  // 预计算每维对数归一化常数, 供在线似然与参考积分复用。
  log_normalizer_.resize(dimension());
  for(int j=0;j<dimension();++j) {
    if(kind_==NoiseKind::normal) {
      require(second_[j]>0,"正态标准差必须严格大于零");
      log_normalizer_[j]=-std::log(second_[j])-0.5*std::log(2*std::numbers::pi);
    } else {
      const double width=second_[j]-first_[j];
      require(second_[j]>first_[j]&&std::isfinite(width),"均匀分布要求有限宽度且 lower < upper");
      log_normalizer_[j]=-std::log(width);
    }
  }
}
Noise Noise::normal(int dim,double mean,double stddev) {
  check_dimension(dim);return normal(Vector::Constant(dim,mean),Vector::Constant(dim,stddev));
}
Noise Noise::normal(Vector mean,Vector stddev) { return {NoiseKind::normal,std::move(mean),std::move(stddev)}; }
Noise Noise::uniform(int dim,double lower,double upper) {
  check_dimension(dim);return uniform(Vector::Constant(dim,lower),Vector::Constant(dim,upper));
}
Noise Noise::uniform(Vector lower,Vector upper) { return {NoiseKind::uniform,std::move(lower),std::move(upper)}; }
double Noise::sample_component(int j,Random& rng) const {
  require(j>=0&&j<dimension(),"噪声分量索引越界");
  const double value=kind_==NoiseKind::normal ? first_[j]+second_[j]*rng.normal()
                                            : std::lerp(first_[j],second_[j],rng.uniform());
  require(std::isfinite(value),"噪声采样数值溢出");return value;
}
void Noise::sample(Out output,Random& rng) const {
  require(output.size()==dimension(),"噪声输出维度不匹配");
  for(int j=0;j<dimension();++j)output[j]=sample_component(j,rng);
  require(output.allFinite(),"噪声采样数值溢出");
}
double Noise::component_log_density(int j,double value) const {
  require(!std::isnan(value),"噪声密度输入不能为 NaN");
  if(!std::isfinite(value))return -INFINITY;
  if(kind_==NoiseKind::uniform)
    return value<first_[j]||value>second_[j] ? -INFINITY : log_normalizer_[j];
  const double standardized=(value-first_[j])/second_[j];
  return log_normalizer_[j]-0.5*standardized*standardized;
}
double Noise::log_density(In value) const {
  require(value.size()==dimension(),"噪声密度输入维度不匹配");
  double result=0;
  for(int j=0;j<dimension();++j)result+=component_log_density(j,value[j]);
  return result;
}
double Noise::log_density_scalar(double value) const {
  require(dimension()==1,"标量密度接口只接受 dim=1");return component_log_density(0,value);
}
void Noise::log_density_scalar_batch(In values,Out output) const {
  require(dimension()==1&&values.size()==output.size(),"批量标量密度的维度错误");
  require(!values.array().isNaN().any(),"批量密度输入不能为 NaN");
  if(kind_==NoiseKind::normal)
    output.array()=log_normalizer_[0]-0.5*((values.array()-first_[0])/second_[0]).square();
  else
    for(Eigen::Index i=0;i<values.size();++i)output[i]=component_log_density(0,values[i]);
}
} // namespace pf
