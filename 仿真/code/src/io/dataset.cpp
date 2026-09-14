#include "pf/dataset.hpp"

namespace pf {
void save_dataset(const fs::path& dir,PublicDataset& data,const TruthDataset& truth,std::uint64_t seed) {
  require(!fs::exists(dir),"数据目录已存在, 请使用新版本目录");fs::create_directories(dir);
  const auto obs=dir/"observations.bin",hidden=dir/"truth.bin";
  Writer w(obs.string()+".partial");w.text("PF_OBS_V1");w.text(data.environment);w.text(data.variant);w.text(data.parameters);
  w.integer(data.trajectories.size());
  for(const auto& t:data.trajectories) { w.integer(t.id);w.integer(t.values.size());for(double y:t.values)w.real(y); }
  w.close();commit_file(obs.string()+".partial",obs);data.hash=sha256(obs);
  Writer tw(hidden.string()+".partial");tw.text("PF_TRUTH_V1");tw.text(data.environment);tw.text(data.variant);tw.text(data.hash);
  tw.integer(truth.trajectories.size());
  for(const auto& t:truth.trajectories) { tw.integer(t.id);tw.matrix(t.initial);tw.matrix(t.states); }
  tw.close();commit_file(hidden.string()+".partial",hidden);
  // 生成种子属于私有清单, 在线滤波命令只读取 observations.bin。
  std::ofstream manifest(dir/"manifest.txt");
  manifest<<"格式=PF_DATA_V1\n环境="<<data.environment<<"\n变体="<<data.variant<<"\n参数="<<data.parameters
    <<"\n数据种子="<<seed<<"\n轨迹数="<<data.trajectories.size()
    <<"\n生成编译器="<<__VERSION__<<"\n随机数=mt19937_64/Box-Muller-v1/stream-hash-v1\n流=初值0,过程1,观测2\n观测SHA256="<<data.hash
    <<"\n真值SHA256="<<sha256(hidden)<<"\n";
  manifest.close();require(bool(manifest),"数据清单写入失败");
}
PublicDataset load_observations(const fs::path& dir) {
  const auto path=dir/"observations.bin";verify_file(path);Reader r(path);
  require(r.text()=="PF_OBS_V1","不支持的观测格式");
  PublicDataset data;data.environment=r.text();data.variant=r.text();data.parameters=r.text();data.hash=sha256(path);
  const auto count=r.integer(100000);require(count>0,"观测集为空");
  for(std::uint64_t i=0;i<count;++i) {
    Observations t;t.id=static_cast<int>(r.integer(100000));require(t.id==static_cast<int>(i),"轨迹编号必须连续且唯一");
    t.values.resize(r.integer(100000));require(!t.values.empty(),"观测轨迹为空");
    for(double& y:t.values) { y=r.real();require(std::isfinite(y),"观测非有限"); }
    data.trajectories.push_back(std::move(t));
  }
  r.end();return data;
}
TruthDataset load_truth(const fs::path& dir) {
  const auto path=dir/"truth.bin";verify_file(path);Reader r(path);
  require(r.text()=="PF_TRUTH_V1","不支持的真值格式");
  TruthDataset data;data.environment=r.text();data.variant=r.text();data.observation_hash=r.text();
  const auto count=r.integer(100000);require(count>0,"真值集为空");
  for(std::uint64_t i=0;i<count;++i) {
    TruthTrajectory t;t.id=static_cast<int>(r.integer(100000));require(t.id==static_cast<int>(i),"真值编号错误");
    t.initial=r.vector();t.states=r.matrix();require(t.initial.allFinite()&&t.states.allFinite(),"真值非有限");
    data.trajectories.push_back(std::move(t));
  }
  r.end();return data;
}
} // namespace pf
