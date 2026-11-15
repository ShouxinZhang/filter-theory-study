#pragma once
#include <map>
#include <cstdint>
#include <string>
#include <stdexcept>
namespace baseline {
// --key value 接口，组合配置交由调度层
class Args {
    std::map<std::string,std::string> values;
public:
    Args(int argc,char** argv) {
        for(int i=1;i<argc;i+=2) {
            if(i+1>=argc || std::string(argv[i]).rfind("--",0)!=0)
                throw std::invalid_argument("参数必须为 --key value");
            if(!values.emplace(std::string(argv[i]).substr(2),argv[i+1]).second)
                throw std::invalid_argument("重复参数");
        }
    }
    std::string get(const std::string& key,const std::string& fallback="") const {
        auto it=values.find(key); return it==values.end()?fallback:it->second;
    }
    std::string require(const std::string& key) const {
        auto v=get(key); if(v.empty()) throw std::invalid_argument("缺少参数 --"+key); return v;
    }
    int integer(const std::string& k,int d) const { return std::stoi(get(k,std::to_string(d))); }
    double real(const std::string& k,double d) const { auto v=get(k); return v.empty()?d:std::stod(v); }
    uint64_t seed() const { return std::stoull(require("seed")); }
};
}
