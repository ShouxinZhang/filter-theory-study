#include "pf/filter.hpp"
#include <cmath>

namespace pf {
ParticleFilter::ParticleFilter(const Environment& model, FilterConfig config, int trajectory)
    : model_(model),config_(std::move(config)),
      initialization_(seed_for(config_.seed,trajectory,10)),
      propagation_(seed_for(config_.seed,trajectory,11)),
      resampling_(seed_for(config_.seed,trajectory,12)) {
  require(config_.particles>0,"粒子数必须为正");
  require(config_.algorithm=="bpf" || config_.algorithm=="etpf","算法只能是 bpf 或 etpf");
  posterior_.resize(model_.dimension(),config_.particles);
  for (int i=0;i<config_.particles;++i) model_.sample_initial(posterior_.col(i),initialization_);
}
FilterStep ParticleFilter::step(int k, double y) {
  require(!failed_,"此滤波器已失败, 请重新初始化");
  require(k==next_k_ && k<=model_.steps(),"观测必须从 k=1 开始严格顺序输入");
  require(std::isfinite(y),"观测必须有限");
  try {
    FilterStep result;
    result.k=k;
    result.predicted.resize(model_.dimension(),config_.particles);
    if (k==1 && model_.initial_time()==1) result.predicted=posterior_;
    else for (int i=0;i<config_.particles;++i)
      model_.propagate(k,posterior_.col(i),result.predicted.col(i),propagation_);
    require(result.predicted.allFinite(),"传播粒子出现非有限值");
    Vector log_weights(config_.particles);
    for (int i=0;i<config_.particles;++i) log_weights[i]=model_.log_likelihood(y,result.predicted.col(i));
    result.weights=normalized_log_weights(log_weights);
    result.mean=result.predicted*result.weights;
    if (config_.algorithm=="bpf") result.posterior=multinomial_resample(result.predicted,result.weights,resampling_);
    else {
      const auto plan=model_.dimension()==1
        ? monotone_transport(result.predicted,result.weights,config_.transport)
        : network_transport(result.predicted,result.weights,config_.transport);
      result.posterior=Matrix::Zero(model_.dimension(),config_.particles);
      for (const auto& mass:plan.masses)
        result.posterior.col(mass.target).noalias()+=config_.particles*mass.value*result.predicted.col(mass.source);
      result.transport=plan.diagnostics;
    }
    require(result.mean.allFinite() && result.posterior.allFinite(),"滤波输出非有限");
    posterior_=result.posterior; // 此复制属于在线计算, 包含在 runner 的计时内。
    ++next_k_;
    return result;
  } catch (...) { failed_=true; throw; }
}
} // namespace pf
