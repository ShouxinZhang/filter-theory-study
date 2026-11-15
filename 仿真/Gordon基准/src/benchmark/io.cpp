#include "baseline/io.hpp"
#include <sstream>
#include <iomanip>
#include <stdexcept>
#include <cmath>
namespace baseline {
std::vector<std::string> split(const std::string& s) {
    std::vector<std::string> v; std::stringstream in(s); std::string a;
    while(std::getline(in,a,',')) v.push_back(a);
    return v;
}
void prepare_parent(const std::filesystem::path& p) {
    if(!p.parent_path().empty()) std::filesystem::create_directories(p.parent_path());
}
void atomic_text(const std::filesystem::path& p,const std::string& text) {
    prepare_parent(p); auto tmp=p; tmp+=".tmp";
    { std::ofstream out(tmp); out<<text; if(!out) throw std::runtime_error("写文件失败"); }
    std::filesystem::rename(tmp,p);
}
template<class Row> std::vector<Row> read_series(const std::filesystem::path& p,const std::string& header) {
    std::ifstream in(p); std::string line;
    if(!std::getline(in,line)||line!=header) throw std::runtime_error("数据表头错误: "+p.string());
    std::vector<Row> out;
    while(std::getline(in,line)) {
        auto c=split(line);
        if(c.size()!=2) throw std::runtime_error("数据列数错误");
        Row r{std::stoi(c[0]),std::stod(c[1])};
        if(r.step!=static_cast<int>(out.size()+1)||!std::isfinite(r.value))
            throw std::runtime_error("时间索引或观测非有限");
        out.push_back(r);
    }
    if(out.empty()) throw std::runtime_error("数据为空");
    return out;
}
std::vector<Observation> read_observations(const std::filesystem::path& p) {return read_series<Observation>(p,"step,y");}
std::vector<Truth> read_truth(const std::filesystem::path& p) {return read_series<Truth>(p,"step,x");}
static const std::string header="step,observed,prior_mean,prior_var,prior_low,prior_high,post_mean,post_var,post_low,post_high,predict_us,update_us,ess,sinkhorn_iterations,sinkhorn_residual,sinkhorn_converged,rounding_l1,transport_cost";
void write_records(const std::filesystem::path& p,const std::vector<Record>& rows) {
    std::ostringstream out; out<<std::setprecision(17)<<header<<'\n';
    for(const auto& r:rows) {
        out<<r.step<<','<<r.observed<<','<<r.prior.mean<<','<<r.prior.variance<<','<<r.prior.low<<','<<r.prior.high
           <<','<<r.posterior.mean<<','<<r.posterior.variance<<','<<r.posterior.low<<','<<r.posterior.high
           <<','<<r.predict_us<<','<<r.update_us<<','<<r.diagnostics.ess<<','<<r.diagnostics.iterations
           <<','<<r.diagnostics.residual<<','<<r.diagnostics.converged<<','<<r.diagnostics.correction
           <<','<<r.diagnostics.transport_cost<<'\n';
    }
    atomic_text(p,out.str());
}
std::vector<Record> read_records(const std::filesystem::path& p) {
    std::ifstream in(p); std::string line;
    if(!std::getline(in,line)||line!=header) throw std::runtime_error("滤波输出表头不匹配");
    std::vector<Record> result;
    while(std::getline(in,line)) {
        auto c=split(line); if(c.size()!=18)throw std::runtime_error("滤波输出列数错误");
        Record r; r.step=std::stoi(c[0]); r.observed=std::stoi(c[1]);
        r.prior={std::stod(c[2]),std::stod(c[3]),std::stod(c[4]),std::stod(c[5])};
        r.posterior={std::stod(c[6]),std::stod(c[7]),std::stod(c[8]),std::stod(c[9])};
        r.predict_us=std::stod(c[10]); r.update_us=std::stod(c[11]);
        r.diagnostics={std::stod(c[12]),std::stod(c[14]),std::stod(c[16]),std::stod(c[17]),std::stoi(c[13]),std::stoi(c[15])};
        if(r.step!=static_cast<int>(result.size()+1)) throw std::runtime_error("在线输出时间索引错误");
        result.push_back(r);
    }
    return result;
}
}
