#pragma once
#include "pf/dataset.hpp"
#include <map>
#include <set>

namespace app {
// 命令行解析与执行分离, 所有未知参数都报错, 防止实验配置拼写错误。
class Options {
 public:
  Options(int argc,char** argv);
  std::string command;
  std::string get(const std::string& key,const std::string& fallback="") const;
  int integer(const std::string& key,int fallback) const;
  std::uint64_t seed(const std::string& key,std::uint64_t fallback) const;
  double real(const std::string& key,double fallback) const;
  bool flag(const std::string& key) const;
  void allow(std::initializer_list<std::string> names) const;
 private:
  std::map<std::string,std::string> values_;
};
void help();
int commands(const Options& options);
int run(const Options& options);
pf::fs::path trajectory_path(const pf::fs::path& directory,int id);
} // namespace app
