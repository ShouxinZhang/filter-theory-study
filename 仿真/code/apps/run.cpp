#include "options.hpp"
#include "pf/filter.hpp"
#include <atomic>
#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>
#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>

namespace app {
using Clock=std::chrono::steady_clock;
static double milliseconds(Clock::time_point begin) { return std::chrono::duration<double,std::milli>(Clock::now()-begin).count(); }
class DirectoryLock {
 public:
  explicit DirectoryLock(const pf::fs::path& directory) {
    descriptor_=::open((directory/".lock").c_str(),O_CREAT|O_RDWR,0600);
    pf::require(descriptor_>=0,"无法创建运行目录锁");
    if(::flock(descriptor_,LOCK_EX|LOCK_NB)!=0) { ::close(descriptor_);throw std::runtime_error("该输出目录正被另一个进程使用"); }
  }
  ~DirectoryLock() { ::flock(descriptor_,LOCK_UN);::close(descriptor_); }
 private:int descriptor_=-1;
};
static bool same(const pf::RunRecord& r,const pf::PublicDataset& data,const pf::FilterConfig& c,int id) {
  return r.data_hash==data.hash&&r.environment==data.environment&&r.variant==data.variant&&r.trajectory==id&&
    r.config.algorithm==c.algorithm&&r.config.particles==c.particles&&r.config.seed==c.seed&&
    r.config.transport.tolerance==c.transport.tolerance&&r.config.transport.max_iterations==c.transport.max_iterations;
}
int run(const Options& o) {
  o.allow({"data","out","algorithm","particles","seed","threads","resume","ot-tolerance","ot-max-iterations"});
  pf::require(!o.get("data").empty()&&!o.get("out").empty(),"run 需要 --data 与 --out");
  const auto data=pf::load_observations(o.get("data"));
  auto model=pf::environment_from_parameters(data.environment,data.parameters);
  for(const auto& t:data.trajectories)pf::require(static_cast<int>(t.values.size())==model->steps(),"观测步数与环境不匹配");
  pf::FilterConfig config;config.algorithm=o.get("algorithm","bpf");config.particles=o.integer("particles",model->dimension()==1?500:4000);
  config.seed=o.seed("seed",20260914);config.transport.tolerance=o.real("ot-tolerance",1e-9);config.transport.max_iterations=o.seed("ot-max-iterations",2000000);
  const int threads=o.integer("threads",1);pf::require(threads>0&&threads<=256,"线程数必须在 1 到 256 之间");
  pf::require(config.particles>0&&config.transport.tolerance>0&&config.transport.tolerance<=1e-4&&config.transport.max_iterations>0,"粒子数或输运参数非法");
  const pf::fs::path out=o.get("out");pf::require(!pf::fs::exists(out)||o.flag("resume"),"输出目录已存在, 续跑请使用 --resume");
  pf::fs::create_directories(out);DirectoryLock lock(out);
  // 独立预热实例, 不消耗正式运行的随机流, 也不写出结果。
  {
    auto warm_config=config;warm_config.particles=std::min(config.particles,64);
    pf::ParticleFilter warm(*model,warm_config,0);
    // 有限支持似然下, 小集合预热失败不代表正式 N 粒子运行必然失败。
    try { warm.step(1,data.trajectories[0].values[0]); }
    catch(const std::exception& e) { std::cout<<"预热未完成, 正式运行单独评估: "<<e.what()<<'\n'; }
  }
  const auto info_path=out/("运行信息-"+std::to_string(std::chrono::system_clock::now().time_since_epoch().count())+".txt");
  std::ofstream info(info_path);info<<"编译器="<<__VERSION__<<"\n构建类型="<<FILTER_BUILD_TYPE<<"\nCPU并发="<<std::thread::hardware_concurrency()
    <<"\n编译选项="<<FILTER_BUILD_FLAGS<<"\n轨迹线程="<<threads<<"\n内核线程=1\n求解器=POT-85113e9/network-simplex;monotone-v1\n随机数=mt19937_64/Box-Muller-v1\n观测SHA256="<<data.hash
    <<"\n算法="<<config.algorithm<<"\n粒子数="<<config.particles<<"\n种子="<<config.seed
    <<"\n输运容差="<<config.transport.tolerance<<"\n输运迭代上限="<<config.transport.max_iterations<<"\n";
  std::ifstream cpu("/proc/cpuinfo");std::string line;while(std::getline(cpu,line))if(line.starts_with("model name")) { info<<line<<'\n';break; }
  info.close();pf::require(bool(info),"运行元数据写入失败");
  std::atomic<std::size_t> next{0};std::atomic<int> failures{0};std::atomic<bool> stop{false};
  std::mutex mutex;std::exception_ptr exception;
  auto worker=[&] {
    try {
      while(!stop) {
        const auto index=next.fetch_add(1);if(index>=data.trajectories.size())break;
        const auto& trajectory=data.trajectories[index];const auto path=trajectory_path(out,trajectory.id);
        if(pf::fs::exists(path)&&!pf::fs::exists(path.string()+".sha256")) {
          // 提交文件与摘要之间被中断: 留存未提交文件再重算, 不把它误当作成功检查点。
          pf::fs::rename(path,path.string()+".interrupted-"+std::to_string(Clock::now().time_since_epoch().count()));
        }
        if(pf::fs::exists(path)) {
          const auto previous=pf::load_run(path);pf::require(same(previous,data,config,trajectory.id),"续跑检查点配置不匹配");
          pf::require(!previous.failure.empty()||static_cast<int>(previous.steps.size())==model->steps(),"续跑检查点不完整");
          if(!previous.failure.empty())++failures;
          continue;
        }
        pf::RunRecord record;record.environment=data.environment;record.variant=data.variant;record.data_hash=data.hash;record.trajectory=trajectory.id;record.config=config;
        record.steps.reserve(model->steps());const auto init=Clock::now();pf::ParticleFilter filter(*model,config,trajectory.id);record.initialization_ms=milliseconds(init);
        for(int k=1;k<=model->steps();++k) {
          try {
            const auto start=Clock::now();auto step=filter.step(k,trajectory.values[k-1]);step.elapsed_ms=milliseconds(start);record.steps.push_back(std::move(step));
            if(config.algorithm=="etpf"&&model->dimension()>1&&k%6==0) {
              std::lock_guard guard(mutex);std::cout<<"轨迹 "<<trajectory.id<<": "<<k<<'/'<<model->steps()<<std::endl;
            }
          } catch(const std::exception& e) { record.failure_k=k;record.failure=e.what();++failures;break; }
        }
        // 本条轨迹完成后才写文件, 文件 I/O 不进入单步滤波计时。
        pf::save_run(path,record);
        std::lock_guard guard(mutex);std::cout<<"轨迹 "<<trajectory.id<<": "<<(record.failure.empty()?"完成":record.failure)<<std::endl;
      }
    } catch(...) { std::lock_guard guard(mutex);if(!exception)exception=std::current_exception();stop=true; }
  };
  std::vector<std::thread> workers;for(int i=0;i<std::min<int>(threads,data.trajectories.size());++i)workers.emplace_back(worker);
  for(auto& t:workers)t.join();
  if(exception)std::rethrow_exception(exception);
  std::cout<<"运行结束, 失败轨迹="<<failures<<'\n';return failures?2:0;
}
} // namespace app
