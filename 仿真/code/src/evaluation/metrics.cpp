#include "pf/evaluation.hpp"
#include <Eigen/Eigenvalues>
#include <cmath>

namespace pf {
static std::vector<std::pair<std::string,std::vector<int>>> groups(int d) {
  if(d==1)return {{"state",{0}}};
  require(d==4,"评估仅支持 1 维或 4 维状态");
  return {{"position",{0,2}},{"velocity",{1,3}},{"x",{0}},{"vx",{1}},{"y",{2}},{"vy",{3}}};
}
TrajectoryEvaluation evaluate_trajectory(const TruthDataset& truth,const RunRecord& run,const ReferenceRecord* ref) {
  require(run.environment==truth.environment && run.variant==truth.variant && run.data_hash==truth.observation_hash,
          "评估数据版本或 SHA-256 不匹配");
  require(run.trajectory>=0 && static_cast<std::size_t>(run.trajectory)<truth.trajectories.size(),"评估轨迹编号越界");
  const auto& states=truth.trajectories[run.trajectory].states;
  const int d=states.rows(),steps=states.cols();
  TrajectoryEvaluation result;result.id=run.trajectory;result.initialization_ms=run.initialization_ms;
  if(!std::isfinite(run.initialization_ms)||run.initialization_ms<0) { result.failure="初始化耗时非法";return result; }
  if(!run.failure.empty()||run.failure_k!=0) { result.failure=run.failure;return result; }
  if(static_cast<int>(run.steps.size())!=steps) { result.failure="滤波结果缺步";return result; }
  if(ref) {
    require(ref->environment==run.environment && ref->variant==run.variant && ref->data_hash==run.data_hash &&
            ref->trajectory==run.trajectory && ref->steps.size()==run.steps.size(),"参考后验版本或索引不匹配");
    require(std::isfinite(ref->mean_precision)&&ref->mean_precision>=0 && std::isfinite(ref->covariance_precision)&&ref->covariance_precision>=0,
            "参考精度字段非法");
  }
  const auto selected=groups(d);
  for(const auto& [name,indices]:selected) { Metrics m;m.group=name;m.components=indices.size();result.metrics.push_back(m); }
  for(int k=0;k<steps;++k) {
    const auto& s=run.steps[k];const int n=run.config.particles;
    if(s.k!=k+1||s.mean.size()!=d||s.predicted.rows()!=d||s.predicted.cols()!=n||s.posterior.rows()!=d||s.posterior.cols()!=n||
       s.weights.size()!=n||n<=0||!s.mean.allFinite()||!s.weights.allFinite()||!s.predicted.allFinite()||!s.posterior.allFinite()||
       s.weights.minCoeff()<0||std::abs(s.weights.sum()-1)>1e-9||!std::isfinite(s.elapsed_ms)||s.elapsed_ms<0||
       (s.predicted*s.weights-s.mean).norm()>1e-9*(1+s.mean.norm())) {
      result.failure="滤波记录的索引, 权重, 均值或维度错误";result.steps.clear();result.metrics.clear();return result;
    }
    const bool has_ref=ref&&ref->validated;
    if(has_ref) {
      const auto& r=ref->steps[k];
      require(r.k==k+1&&r.mean.size()==d&&r.covariance.rows()==d&&r.covariance.cols()==d&&r.mean.allFinite()&&r.covariance.allFinite(),"参考后验记录非法");
      require((r.covariance-r.covariance.transpose()).norm()<1e-9,"参考协方差不对称");
      Eigen::SelfAdjointEigenSolver<Matrix> eig(r.covariance);
      require(eig.info()==Eigen::Success&&eig.eigenvalues().minCoeff()>=-1e-12,"参考协方差非半正定");
    }
    const Vector error=s.mean-states.col(k);
    for(std::size_t g=0;g<selected.size();++g) {
      StepMetrics out;out.trajectory=run.trajectory;out.k=k+1;out.group=selected[g].first;out.error=error;
      out.ess=1/s.weights.squaredNorm();out.mean_shift=(s.posterior.rowwise().mean()-s.mean).norm();out.elapsed_ms=s.elapsed_ms;
      if(has_ref) { out.bayes_mse_ref=0;out.excess_mse_ref=0; }
      for(int j:selected[g].second) {
        out.squared_error+=error[j]*error[j];out.absolute_error+=std::abs(error[j]);
        if(has_ref) {
          out.bayes_mse_ref+=std::max(0.0,ref->steps[k].covariance(j,j));
          const double delta=s.mean[j]-ref->steps[k].mean[j];out.excess_mse_ref+=delta*delta;
        }
      }
      auto& m=result.metrics[g];m.squared_error+=out.squared_error;m.absolute_error+=out.absolute_error;++m.samples;
      if(has_ref) {
        m.bayes_mse+=out.bayes_mse_ref;m.excess_mse+=out.excess_mse_ref;++m.reference_samples;
        m.mean_precision=ref->mean_precision;m.covariance_precision=ref->covariance_precision;
      }
      result.steps.push_back(std::move(out));
    }
  }
  result.success=true;return result;
}
} // namespace pf
