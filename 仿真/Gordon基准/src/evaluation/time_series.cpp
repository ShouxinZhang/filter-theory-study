#include "baseline/time_series.hpp"
#include "baseline/io.hpp"
#include <cmath>
#include <map>
#include <set>
#include <sstream>
#include <iomanip>
#include <stdexcept>
namespace baseline {
void TimeSeriesAccumulator::add(const std::vector<Truth>& truth,const std::vector<Record>& records) {
    if(truth.empty()||truth.size()!=records.size())throw std::invalid_argument("时序评估长度不一致");
    if(sums.empty())sums.resize(truth.size());
    if(sums.size()!=truth.size())throw std::invalid_argument("同一配置的轨迹长度不一致");
    for(size_t k=0;k<truth.size();++k) {
        const auto& r=records[k];const auto&t=truth[k];auto&s=sums[k];
        if(t.step!=static_cast<int>(k+1)||r.step!=t.step||(r.observed!=0&&r.observed!=1))
            throw std::invalid_argument("时序评估索引或观测标记错误");
        if(s.trials>0&&s.observed!=r.observed)throw std::invalid_argument("同一配置的观测时刻不一致");
        double error=r.posterior.mean-t.value,prior_error=r.prior.mean-t.value;
        if(!std::isfinite(error*error)||!std::isfinite(prior_error*prior_error))
            throw std::invalid_argument("时序评估输入非有限");
        s.step=t.step;s.observed=r.observed;s.trials++;
        s.posterior+=error*error;s.prior+=prior_error*prior_error;
    }
}
std::vector<TimeSeriesPoint> TimeSeriesAccumulator::result()const {
    std::vector<TimeSeriesPoint> points;double cumulative=0,count=0;
    for(const auto&s:sums) {
        cumulative+=s.posterior;count+=s.trials;
        points.push_back({s.step,s.observed,s.trials,std::sqrt(s.posterior/s.trials),
                          std::sqrt(s.prior/s.trials),std::sqrt(cumulative/count)});
    }
    return points;
}
void summarize_time_series(const std::filesystem::path& index,const std::filesystem::path& output) {
    std::ifstream in(index);std::string line;
    if(!std::getline(in,line)||line!="config_id,algorithm,n,epsilon,interval,trial,truth_path,filter_path")
        throw std::runtime_error("时序索引表头错误");
    struct Group {
        std::vector<std::string> metadata;
        std::set<int> trials;
        TimeSeriesAccumulator accumulator;
    };
    std::map<std::string,Group> groups;
    while(std::getline(in,line)) {
        auto c=split(line);if(c.size()!=8)throw std::runtime_error("时序索引列数错误");
        auto&g=groups[c[0]];std::vector<std::string> metadata(c.begin(),c.begin()+5);
        if(!g.metadata.empty()&&g.metadata!=metadata)throw std::runtime_error("时序配置标识冲突");
        if(!g.trials.insert(std::stoi(c[5])).second)throw std::runtime_error("时序索引重复轨迹");
        g.metadata=metadata;
        g.accumulator.add(read_truth(c[6]),read_records(c[7]));
    }
    if(groups.empty())throw std::runtime_error("没有可用的时序数据");
    std::ostringstream out;out<<std::setprecision(17)
        <<"config_id,algorithm,n,epsilon,interval,step,trials,observed,rmse,prior_rmse,cumulative_rmse\n";
    for(const auto&[key,g]:groups) {
        for(const auto&p:g.accumulator.result()) {
            for(size_t j=0;j<g.metadata.size();++j)out<<(j?",":"")<<g.metadata[j];
            out<<','<<p.step<<','<<p.trials<<','<<p.observed<<','<<p.rmse<<','<<p.prior_rmse
               <<','<<p.cumulative_rmse<<'\n';
        }
    }
    atomic_text(output,out.str());
}
}
