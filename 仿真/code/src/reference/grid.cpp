#include "pf/reference.hpp"
#include "pf/environment.hpp"
#include <cmath>
#include <iomanip>
#include <sstream>

namespace pf {
std::string grid_method(const GridConfig& config) {
  std::ostringstream result;
  result<<std::setprecision(17)<<"grid-v1:h="<<config.spacing<<";L="<<config.bound<<";tol="<<config.tolerance;
  return result.str();
}
static std::vector<ReferenceStep> solve(const Environment& model,const Observations& obs,double bound,double spacing,bool midpoint) {
  const int bins=static_cast<int>(std::ceil(2*bound/spacing));
  const int n=midpoint?bins:bins+1;
  require(n<=8193,"参考网格过大, 请调整边界或步长");
  const double dx=2*bound/bins;
  Vector grid(n),quadrature=Vector::Constant(n,dx),weights(n);
  for(int i=0;i<n;++i)grid[i]=-bound+(i+(midpoint?0.5:0))*dx;
  if(!midpoint) { quadrature[0]*=0.5;quadrature[n-1]*=0.5; }
  weights=(-grid.array().square()/4).exp()*quadrature.array();weights/=weights.sum();
  std::vector<ReferenceStep> output;output.reserve(obs.values.size());
  Vector drift(n),log_weights(n),residuals(n),kernel(n);
  for(std::size_t t=0;t<obs.values.size();++t) {
    const int k=static_cast<int>(t)+1;
    for(int i=0;i<n;++i)drift[i]=gordon_drift(k,grid[i]);
    const Vector previous_log_weights=weights.array().log();
    for(int j=0;j<n;++j) {
      // 共用噪声密度接口, 在对数域累加预测核以避免尾部下溢。
      residuals.array()=grid[j]-drift.array();
      model.process_noise().log_density_scalar_batch(residuals,kernel);
      kernel+=previous_log_weights;
      const double maximum=kernel.maxCoeff();
      const double log_prediction=maximum==-INFINITY ? -INFINITY :
        maximum+std::log((kernel.array()-maximum).exp().sum());
      const double residual=obs.values[t]-grid[j]*grid[j]/20;
      log_weights[j]=log_prediction+std::log(quadrature[j])+model.observation_noise().log_density_scalar(residual);
    }
    weights=normalized_log_weights(log_weights);
    ReferenceStep step;step.k=k;step.mean=Vector::Constant(1,grid.dot(weights));
    step.covariance=Matrix::Constant(1,1,((grid.array()-step.mean[0]).square()*weights.array()).sum());
    output.push_back(std::move(step));
  }
  return output;
}
ReferenceRecord grid_reference(const PublicDataset& data,const Observations& obs,const GridConfig& config) {
  require(data.environment=="gordon-v1","当前内置参考求解器仅支持 Gordon 一维; 四维结果可先独立评估真值误差");
  const auto model=environment_from_parameters(data.environment,data.parameters);
  require(std::isfinite(config.spacing)&&config.spacing>0 && std::isfinite(config.bound)&&config.bound>0 &&
          std::isfinite(config.tolerance)&&config.tolerance>0,"网格参数必须为有限正数");
  require(2*config.bound*1.25/(config.spacing/4)<=8192,"扩域后的参考网格超过 8192 个区间");
  auto coarse=solve(*model,obs,config.bound,config.spacing,true);
  auto middle=solve(*model,obs,config.bound,config.spacing/2,true);
  auto fine=solve(*model,obs,config.bound,config.spacing/4,true);
  auto expanded=solve(*model,obs,config.bound*1.25,config.spacing/4,true);
  auto cross=solve(*model,obs,config.bound*1.25,config.spacing/4,false);
  ReferenceRecord ref;ref.environment=data.environment;ref.variant=data.variant;ref.data_hash=data.hash;ref.trajectory=obs.id;
  ref.method=grid_method(config);
  // 用末两级差异估计精度, 粗网格用于检查误差递减趋势, 不是要求粗网格已足够精确。
  double coarse_mean=0,coarse_covariance=0;
  for(std::size_t k=0;k<coarse.size();++k) {
    coarse_mean=std::max(coarse_mean,(coarse[k].mean-middle[k].mean).cwiseAbs().maxCoeff());
    coarse_covariance=std::max(coarse_covariance,(coarse[k].covariance-middle[k].covariance).cwiseAbs().maxCoeff());
  }
  auto compare=[&](const auto& a,const auto& b) {
    for(std::size_t k=0;k<a.size();++k) {
      ref.mean_precision=std::max(ref.mean_precision,(a[k].mean-b[k].mean).cwiseAbs().maxCoeff());
      ref.covariance_precision=std::max(ref.covariance_precision,(a[k].covariance-b[k].covariance).cwiseAbs().maxCoeff());
    }
  };
  compare(middle,fine);compare(fine,expanded);compare(expanded,cross);
  ref.validated=ref.mean_precision<=config.tolerance && ref.covariance_precision<=config.tolerance &&
    ref.mean_precision<=coarse_mean+config.tolerance && ref.covariance_precision<=coarse_covariance+config.tolerance;
  ref.steps=std::move(cross);return ref;
}
} // namespace pf
