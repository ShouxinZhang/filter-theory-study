#include "test.hpp"
#include "pf/dataset.hpp"
#include "pf/filter.hpp"
#include "pf/evaluation.hpp"
#include "pf/reference.hpp"
#include <chrono>

namespace test {
void integration() {
  const auto temp=pf::fs::temp_directory_path()/("pf-tests-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
  pf::fs::create_directories(temp);
  pf::generate_dataset(temp/"a","gordon","fixed",2,197);
  pf::generate_dataset(temp/"b","gordon","fixed",2,197);
  const auto data=pf::load_observations(temp/"a");const auto truth=pf::load_truth(temp/"a");
  check(data.hash==pf::load_observations(temp/"b").hash,"数据冻结可复现");near(truth.trajectories[0].initial[0],0.1,0,"固定真实初值");
  // 与拆分前的物理采样公式逐位比较, 默认环境不能因接口重构而换数据。
  pf::Random legacy_process(pf::seed_for(197,0,1)),legacy_observation(pf::seed_for(197,0,2));
  double legacy_state=0.1;
  for(int k=1;k<=50;++k) {
    legacy_state=pf::gordon_drift(k,legacy_state)+std::sqrt(10.0)*legacy_process.normal();
    near(truth.trajectories[0].states(0,k-1),legacy_state,0,"默认真实状态兼容");
    near(data.trajectories[0].values[k-1],legacy_state*legacy_state/20+legacy_observation.normal(),0,"默认观测兼容");
  }
  auto model=pf::make_environment(data.environment);pf::FilterConfig c;c.particles=100;c.algorithm="bpf";
  pf::ParticleFilter bpf(*model,c,0),prefix(*model,c,0);c.algorithm="etpf";pf::ParticleFilter etpf(*model,c,0);
  pf::RunRecord run;run.environment=data.environment;run.variant=data.variant;run.data_hash=data.hash;run.config=c;
  for(int k=1;k<=50;++k) {
    const double y=data.trajectories[0].values[k-1];const auto b=bpf.step(k,y),e=etpf.step(k,y),same=prefix.step(k,y);
    near((b.mean-same.mean).norm(),0,0,"相同观测前缀确定相同在线输出");
    if(k==1) { near((b.predicted-e.predicted).norm(),0,0,"算法共享先验与传播随机流");near((b.weights-e.weights).norm(),0,0,"首步公共加权"); }
    near((e.posterior.rowwise().mean()-e.mean).norm(),0,1e-9,"逐步 ETPF 均值守恒");run.steps.push_back(e);
  }
  throws([&]{bpf.step(51,0);},"不能使用超出环境的观测");
  pf::save_run(temp/"run.bin",run);auto loaded=pf::load_run(temp/"run.bin");
  near((loaded.steps.back().posterior-run.steps.back().posterior).norm(),0,0,"二进制粒子记录无损往返");
  auto evaluation=pf::evaluate_trajectory(truth,loaded);check(evaluation.success,"独立真值评估成功");
  pf::write_report(temp/"report",{evaluation});check(pf::fs::exists(temp/"report/metrics.csv"),"评估报告生成");
  // 直接构造可手算的风险分解, 独立于任何滤波器实现。
  pf::TruthDataset toy;toy.environment="toy";toy.variant="matched-prior";toy.observation_hash="hash";
  pf::TruthTrajectory tt;tt.states.resize(1,2);tt.states<<1,3;toy.trajectories.push_back(tt);
  pf::RunRecord tr;tr.environment="toy";tr.variant=toy.variant;tr.data_hash="hash";tr.config.particles=1;
  pf::ReferenceRecord reference;reference.environment="toy";reference.variant=toy.variant;reference.data_hash="hash";reference.validated=true;
  for(int k=1;k<=2;++k) {
    pf::FilterStep s;s.k=k;s.mean=pf::Vector::Constant(1,k==1?2:1);s.predicted=s.mean;s.posterior=s.mean;s.weights=pf::Vector::Ones(1);tr.steps.push_back(s);
    pf::ReferenceStep r;r.k=k;r.mean=pf::Vector::Constant(1,k==1?1.5:2);r.covariance=pf::Matrix::Constant(1,1,k==1?0.25:0.75);reference.steps.push_back(r);
  }
  const auto risk=pf::evaluate_trajectory(toy,tr,&reference).metrics.front();
  near(risk.squared_error/risk.samples,2.5,1e-14,"先平方后平均的真值 MSE");
  near(risk.bayes_mse/risk.samples,0.5,1e-14,"最优后验 MSE");near(risk.excess_mse/risk.samples,0.625,1e-14,"额外 MSE");
  near(risk.excess_mse/risk.bayes_mse,1.25,1e-14,"相对额外误差");
  reference.validated=false;check(pf::evaluate_trajectory(toy,tr,&reference).metrics.front().reference_samples==0,"未验证参考不能计算正式相对误差");
  tr.steps.pop_back();check(!pf::evaluate_trajectory(toy,tr).success,"缺步轨迹计入失败");
  auto corrupted=temp/"run.bin";{ std::ofstream file(corrupted,std::ios::app);file<<'x'; }
  throws([&]{pf::load_run(corrupted);},"损坏结果必须被 SHA 检出");
  pf::fs::remove_all(temp); // 只清理由本测试创建的唯一临时目录。
}
} // namespace test
