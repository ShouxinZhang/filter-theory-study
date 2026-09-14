#include "options.hpp"
#include <charconv>
#include <cmath>
#include <iostream>

namespace app {
Options::Options(int argc,char** argv) {
  command=argc>1?argv[1]:"help";
  for(int i=2;i<argc;++i) {
    std::string key=argv[i];pf::require(key.starts_with("--"),"参数必须以 -- 开头");key=key.substr(2);
    pf::require(!values_.contains(key),"参数重复: "+key);
    if(key=="resume")values_[key]="true";
    else { pf::require(i+1<argc,"参数缺少值: "+key);values_[key]=argv[++i]; }
  }
}
std::string Options::get(const std::string& key,const std::string& fallback) const {
  const auto it=values_.find(key);return it==values_.end()?fallback:it->second;
}
std::uint64_t Options::seed(const std::string& key,std::uint64_t fallback) const {
  const auto s=get(key,std::to_string(fallback));std::uint64_t value=0;
  const auto [ptr,error]=std::from_chars(s.data(),s.data()+s.size(),value);
  pf::require(error==std::errc()&&ptr==s.data()+s.size(),"无效无符号整数: "+key);return value;
}
int Options::integer(const std::string& key,int fallback) const {
  const auto value=seed(key,fallback);pf::require(value<=10000000,"整数参数过大: "+key);return static_cast<int>(value);
}
double Options::real(const std::string& key,double fallback) const {
  if(!values_.contains(key))return fallback;
  const auto s=get(key);std::size_t used=0;const auto value=std::stod(s,&used);
  pf::require(used==s.size()&&std::isfinite(value),"无效实数: "+key);return value;
}
bool Options::flag(const std::string& key) const { return values_.contains(key); }
void Options::allow(std::initializer_list<std::string> names) const {
  const std::set<std::string> allowed(names);
  for(const auto& [key,value]:values_) { (void)value;pf::require(allowed.contains(key),"未知参数: --"+key); }
}
pf::fs::path trajectory_path(const pf::fs::path& directory,int id) { return directory/("trajectory-"+std::to_string(id)+".bin"); }
void help() {
  std::cout<<"C++ 滤波基准\n"
    <<"generate --env gordon|tracking --out 目录 [--trajectories 100 --seed 1993 --variant fixed|matched-prior]\n"
    <<"    [--process-noise normal|uniform --process-dim d --process-mean 0 --process-std 1]\n"
    <<"    [--process-lower -1 --process-upper 1], 观测噪声使用相同参数并将 process 换成 observation\n"
    <<"    参数支持单值广播或逗号分隔的逐维列表; std 是标准差, run 自动读取冻结配置\n"
    <<"run --data 数据目录 --out 结果目录 --algorithm bpf|etpf [--particles N --seed 20260914 --threads 1 --resume]\n"
    <<"    [--ot-tolerance 1e-9 --ot-max-iterations 2000000]\n"
    <<"reference --data 一维数据目录 --out 参考目录 [--spacing 0.125 --bound 64 --tolerance 1e-5 --resume]\n"
    <<"evaluate --data 数据目录 --runs 结果目录 --out 报告目录 [--reference 参考目录]\n"
    <<"export --file 单轨迹结果.bin --out 均值.csv\n";
}
} // namespace app
