#include "pf/evaluation.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <map>

namespace pf {
static void number(std::ostream& out,double value) { if(std::isfinite(value))out<<value;else out<<"NA"; }
static void metric_row(std::ostream& out,const std::string& scope,const Metrics& m,bool available) {
  out<<scope<<','<<m.group<<','<<m.samples<<',';
  number(out,available&&m.samples?std::sqrt(m.squared_error/m.samples):missing);out<<',';
  number(out,available&&m.samples?m.absolute_error/(m.samples*m.components):missing);out<<',';
  const bool reference=available&&m.samples>0&&m.reference_samples==m.samples;
  const double b=reference?m.bayes_mse/m.samples:missing,d=reference?m.excess_mse/m.samples:missing;
  number(out,b);out<<',';number(out,d);out<<',';number(out,std::sqrt(d));out<<',';
  const double rho=reference&&b>m.components*m.covariance_precision&&b>0?d/b:missing;
  number(out,rho);out<<',';number(out,std::sqrt(rho));out<<',';number(out,1+rho);out<<',';number(out,std::sqrt(1+rho));out<<',';
  number(out,reference?m.mean_precision:missing);out<<',';number(out,reference?m.covariance_precision:missing);out<<'\n';
}
void write_report(const fs::path& directory,const std::vector<TrajectoryEvaluation>& evaluations) {
  require(!evaluations.empty(),"没有可评估轨迹");require(!fs::exists(directory),"报告目录已存在, 请指定新目录");
  fs::create_directories(directory);
  std::ofstream detail(directory/"steps.csv"),summary(directory/"metrics.csv"),status(directory/"status.csv"),timing(directory/"timing.csv"),by_time(directory/"by_time.csv");
  for(auto* f:{&detail,&summary,&status,&timing,&by_time}) { f->exceptions(std::ios::badbit|std::ios::failbit);*f<<std::setprecision(17); }
  detail<<"trajectory,k,group,squared_error,component_mae,ess,mean_shift,elapsed_ms,bayes_mse_ref,excess_mse_ref,error_0,error_1,error_2,error_3\n";
  summary<<"scope,group,samples,rmse,component_mae,bayes_mse_ref,excess_mse_ref,excess_rmse_ref,rho_ref,relative_excess_rmse_ref,posterior_mse_ratio_ref,posterior_rmse_ratio_ref,reference_mean_precision,reference_covariance_precision\n";
  status<<"trajectory,success,reason\n";
  timing<<"trajectory,initialization_ms,total_filter_ms,median_step_ms,p95_step_ms\n";
  by_time<<"k,group,complete_trajectories,rmse_success_subset\n";
  std::map<std::string,Metrics> total;
  std::map<std::pair<int,std::string>,std::pair<double,int>> temporal;
  int failures=0;
  for(const auto& t:evaluations) {
    status<<t.id<<','<<t.success<<','<<std::quoted(t.failure)<<'\n';
    if(!t.success) { ++failures;continue; }
    std::vector<double> times;
    for(const auto& row:t.steps) {
      const auto it=std::find_if(t.metrics.begin(),t.metrics.end(),[&](const auto& m){return m.group==row.group;});
      detail<<t.id<<','<<row.k<<','<<row.group<<','<<row.squared_error<<','<<row.absolute_error/it->components<<','
            <<row.ess<<','<<row.mean_shift<<','<<row.elapsed_ms<<',';
      number(detail,row.bayes_mse_ref);detail<<',';number(detail,row.excess_mse_ref);
      for(int j=0;j<4;++j) { detail<<',';number(detail,j<row.error.size()?row.error[j]:missing); }
      detail<<'\n';
      auto& a=temporal[{row.k,row.group}];a.first+=row.squared_error;++a.second;
      if(row.group==t.metrics.front().group)times.push_back(row.elapsed_ms);
    }
    double elapsed=0;for(double value:times)elapsed+=value;std::sort(times.begin(),times.end());
    timing<<t.id<<','<<t.initialization_ms<<','<<elapsed<<','<<times[(times.size()-1)/2]<<','<<times[static_cast<std::size_t>(std::ceil(0.95*times.size()))-1]<<'\n';
    for(const auto& m:t.metrics) {
      metric_row(summary,"trajectory-"+std::to_string(t.id),m,true);
      auto& a=total[m.group];a.group=m.group;a.components=m.components;a.samples+=m.samples;
      a.squared_error+=m.squared_error;a.absolute_error+=m.absolute_error;a.bayes_mse+=m.bayes_mse;a.excess_mse+=m.excess_mse;
      a.reference_samples+=m.reference_samples;a.mean_precision=std::max(a.mean_precision,m.mean_precision);a.covariance_precision=std::max(a.covariance_precision,m.covariance_precision);
    }
  }
  for(const auto& [name,m]:total) {
    metric_row(summary,"all",m,failures==0);
    if(failures)metric_row(summary,"complete-success-subset",m,true);
  }
  for(const auto& [key,value]:temporal)by_time<<key.first<<','<<key.second<<','<<value.second<<','<<std::sqrt(value.first/value.second)<<'\n';
  std::ofstream note(directory/"说明.txt");note<<"总轨迹="<<evaluations.size()<<"\n失败轨迹="<<failures
    <<"\n参考缺失或未验证时额外误差记 NA; ref 是数值参考, 不是解析精确后验。\n有失败时全集 RMSE 不可用; 成功子集与逐时刻统计明确单列。\n跨算法有失败时请按 status.csv 取共同成功轨迹, 不直接比较各自成功子集。\n固定初值环境的后验风险不是实际真值 MSE 的严格分解。\n";
  require(bool(note),"报告说明写入失败");
}
} // namespace pf
