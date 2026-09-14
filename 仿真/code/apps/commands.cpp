#include "options.hpp"
#include "pf/environment.hpp"
#include "pf/evaluation.hpp"
#include "pf/reference.hpp"
#include <iomanip>
#include <iostream>

namespace app {
static pf::fs::path required(const Options& o,const std::string& key) {
  pf::require(!o.get(key).empty(),"缺少 --"+key);return o.get(key);
}
int commands(const Options& o) {
  if(o.command=="generate") {
    o.allow({"env","out","trajectories","seed","variant",
      "process-noise","process-dim","process-mean","process-std","process-lower","process-upper",
      "observation-noise","observation-dim","observation-mean","observation-std","observation-lower","observation-upper"});
    const auto name=o.get("env","gordon");
    pf::generate_dataset(required(o,"out"),name,o.get("variant","fixed"),o.integer("trajectories",100),o.seed("seed",1993),noise_options(o,name));
    std::cout<<"数据集已冻结: "<<o.get("out")<<'\n';return 0;
  }
  if(o.command=="reference") {
    o.allow({"data","out","spacing","bound","tolerance","resume"});
    const auto data=pf::load_observations(required(o,"data"));const auto out=required(o,"out");
    pf::require(data.environment=="gordon-v1","内置网格参考仅支持一维, 四维可先运行真值误差评估");
    pf::require(!pf::fs::exists(out)||o.flag("resume"),"参考目录已存在, 续跑请使用 --resume");pf::fs::create_directories(out);
    pf::GridConfig config{o.real("spacing",0.125),o.real("bound",64),o.real("tolerance",1e-5)};
    const auto method=pf::grid_method(config);
    int failed=0;
    for(const auto& trajectory:data.trajectories) {
      const auto path=trajectory_path(out,trajectory.id);
      if(pf::fs::exists(path)) {
        const auto ref=pf::load_reference(path);pf::require(ref.data_hash==data.hash&&ref.method==method&&ref.trajectory==trajectory.id,"参考续跑配置不匹配");
        if(!ref.validated)++failed;
        continue;
      }
      const auto ref=pf::grid_reference(data,trajectory,config);pf::save_reference(path,ref);
      std::cout<<"参考轨迹 "<<trajectory.id<<": 均值差="<<ref.mean_precision<<", 协方差差="<<ref.covariance_precision<<", 验证="<<ref.validated<<std::endl;
      if(!ref.validated)++failed;
    }
    return failed?2:0;
  }
  if(o.command=="evaluate") {
    o.allow({"data","runs","out","reference"});const auto directory=required(o,"data");
    const auto observed=pf::load_observations(directory);const auto truth=pf::load_truth(directory);const auto runs=required(o,"runs");
    pf::require(observed.hash==truth.observation_hash && observed.trajectories.size()==truth.trajectories.size(),"真值与观测不对应");
    std::vector<pf::TrajectoryEvaluation> results;
    std::string algorithm;int particles=0;std::uint64_t seed=0;
    for(const auto& t:truth.trajectories) {
      const auto path=trajectory_path(runs,t.id);
      if(!pf::fs::exists(path)) { pf::TrajectoryEvaluation e;e.id=t.id;e.failure="结果缺失";results.push_back(e);continue; }
      const auto record=pf::load_run(path);
      pf::require(record.trajectory==t.id,"结果文件名与轨迹编号不符");
      if(algorithm.empty()) { algorithm=record.config.algorithm;particles=record.config.particles;seed=record.config.seed; }
      pf::require(algorithm==record.config.algorithm&&particles==record.config.particles&&seed==record.config.seed,"不能混合算法, 粒子数或随机种子表汇总");
      if(o.get("reference").empty())results.push_back(pf::evaluate_trajectory(truth,record));
      else {
        const auto ref=pf::load_reference(trajectory_path(o.get("reference"),t.id));
        results.push_back(pf::evaluate_trajectory(truth,record,&ref));
      }
    }
    pf::write_report(required(o,"out"),results);std::cout<<"评估报告已写入: "<<o.get("out")<<'\n';return 0;
  }
  if(o.command=="export") {
    o.allow({"file","out"});const auto run=pf::load_run(required(o,"file"));const auto path=required(o,"out");
    pf::require(!pf::fs::exists(path),"导出文件已存在");std::ofstream out(path);out.exceptions(std::ios::badbit|std::ios::failbit);out<<std::setprecision(17);
    out<<"trajectory,k";if(!run.steps.empty())for(int j=0;j<run.steps.front().mean.size();++j)out<<",mean_"<<j;out<<'\n';
    for(const auto& s:run.steps) { out<<run.trajectory<<','<<s.k;for(double x:s.mean)out<<','<<x;out<<'\n'; }
    return 0;
  }
  throw std::runtime_error("未知命令: "+o.command);
}
} // namespace app
