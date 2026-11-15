#include "baseline/evaluation.hpp"
#include "baseline/io.hpp"
#include <sstream>
#include <iomanip>
#include <cmath>
#include <stdexcept>
#include <map>
#include <algorithm>
#include <random>
namespace baseline {
static std::vector<double*> fields(Metrics& m) {
    return {&m.samples,&m.sse,&m.observations,&m.pre_sse,&m.post_sse,&m.common,&m.common_pre_sse,
            &m.common_post_sse,&m.covered,&m.width,&m.predict_us,&m.update_us,&m.ess_sum,&m.ess_count,
            &m.ot_updates,&m.ot_failed,&m.residual_max,&m.correction_max,&m.iterations};
}
static const std::string header="samples,sse,observations,pre_sse,post_sse,common,common_pre_sse,common_post_sse,covered,width,predict_us,update_us,ess_sum,ess_count,ot_updates,ot_failed,residual_max,correction_max,iterations";
Metrics evaluate(const std::vector<Truth>& truth,const std::vector<Record>& records,int common_interval) {
    if(truth.empty()||truth.size()!=records.size()||common_interval<1)throw std::invalid_argument("评估输入长度错误");
    Metrics m;
    for(size_t i=0;i<truth.size();++i) {
        const auto&r=records[i];double x=truth[i].value;
        if(r.step!=truth[i].step||(r.observed!=0&&r.observed!=1))throw std::runtime_error("评估索引或标记错误");
        for(double z:{x,r.prior.mean,r.posterior.mean,r.posterior.variance,r.posterior.low,r.posterior.high})
            if(!std::isfinite(z))throw std::runtime_error("评估输入非有限");
        if(r.posterior.variance<0||r.posterior.low>r.posterior.high)throw std::runtime_error("后验区间错误");
        double pre=std::pow(r.prior.mean-x,2),post=std::pow(r.posterior.mean-x,2);
        m.samples++;m.sse+=post;m.covered+=x>=r.posterior.low&&x<=r.posterior.high;
        m.width+=r.posterior.high-r.posterior.low;m.predict_us+=r.predict_us;m.update_us+=r.update_us;
        if(r.observed) {
            m.observations++;m.pre_sse+=pre;m.post_sse+=post;
            if(r.step%common_interval==0){m.common++;m.common_pre_sse+=pre;m.common_post_sse+=post;}
            if(std::isfinite(r.diagnostics.ess)){m.ess_sum+=r.diagnostics.ess;m.ess_count++;}
            if(r.diagnostics.converged>=0) {
                m.ot_updates++;m.ot_failed+=r.diagnostics.converged==0;m.iterations+=r.diagnostics.iterations;
                m.residual_max=std::max(m.residual_max,r.diagnostics.residual);
                m.correction_max=std::max(m.correction_max,r.diagnostics.correction);
            }
        }
    }
    if(!std::isfinite(m.sse))throw std::runtime_error("评估误差溢出");
    return m;
}
void write_metrics(const std::filesystem::path& p,const Metrics& input) {
    auto m=input;std::ostringstream out;out<<std::setprecision(17)<<header<<'\n';auto f=fields(m);
    for(size_t i=0;i<f.size();++i)out<<(i?",":"")<<*f[i];
    out<<'\n';atomic_text(p,out.str());
}
Metrics read_metrics(const std::filesystem::path& p) {
    std::ifstream in(p);std::string line;
    if(!std::getline(in,line)||line!=header||!std::getline(in,line))throw std::runtime_error("评估文件损坏");
    auto c=split(line);Metrics m;auto f=fields(m);
    if(c.size()!=f.size())throw std::runtime_error("评估指标列数错误");
    for(size_t i=0;i<f.size();++i)*f[i]=std::stod(c[i]);
    return m;
}
static double ratio(double a,double b) {return b>0?a/b:missing();}
void summarize(const std::filesystem::path& index,const std::filesystem::path& output,int boot) {
    std::ifstream in(index);std::string line;
    if(!std::getline(in,line)||line!="config_id,algorithm,n,epsilon,interval,trial,metrics_path")
        throw std::runtime_error("汇总索引错误");
    struct Group {std::vector<std::string> info;std::vector<Metrics> trials;};
    std::map<std::string,Group> groups;
    while(std::getline(in,line)) {
        auto c=split(line);if(c.size()!=7)throw std::runtime_error("汇总索引列数错误");
        auto&g=groups[c[0]];g.info=c;g.trials.push_back(read_metrics(c[6]));
    }
    std::ostringstream out;out<<std::setprecision(17)
      <<"config_id,algorithm,n,epsilon,interval,trials,rmse,ci_low,ci_high,pre_rmse,post_rmse,common_pre_rmse,common_post_rmse,coverage,interval_width,predict_us_per_step,update_us_per_observation,compute_seconds,ess_mean,ot_updates,ot_nonconverged_fraction,ot_residual_max,rounding_l1_max,ot_iterations_mean\n";
    for(auto&[key,g]:groups) {
        Metrics sum;
        for(auto t:g.trials) {
            auto dst=fields(sum),src=fields(t);
            for(size_t i=0;i<dst.size();++i) {
                if(i==16||i==17)*dst[i]=std::max(*dst[i],*src[i]);else *dst[i]+=*src[i];
            }
        }
        // 对整条轨迹重抽样，保留轨迹内部时间相关性
        std::vector<double> draws;std::mt19937_64 rng(20260907);
        if(g.trials.size()>1 && boot>=20) {
            std::uniform_int_distribution<size_t> pick(0,g.trials.size()-1);
            for(int b=0;b<boot;++b) {
                double sse=0,n=0;
                for(size_t i=0;i<g.trials.size();++i){const auto&t=g.trials[pick(rng)];sse+=t.sse;n+=t.samples;}
                draws.push_back(std::sqrt(sse/n));
            }
            std::sort(draws.begin(),draws.end());
        }
        double low=draws.empty()?missing():draws[static_cast<size_t>(0.025*(draws.size()-1))];
        double high=draws.empty()?missing():draws[static_cast<size_t>(0.975*(draws.size()-1))];
        for(int i=0;i<5;++i)out<<(i?",":"")<<g.info[i];
        out<<','<<g.trials.size()<<','<<std::sqrt(sum.sse/sum.samples)<<','<<low<<','<<high
           <<','<<std::sqrt(ratio(sum.pre_sse,sum.observations))<<','<<std::sqrt(ratio(sum.post_sse,sum.observations))
           <<','<<std::sqrt(ratio(sum.common_pre_sse,sum.common))<<','<<std::sqrt(ratio(sum.common_post_sse,sum.common))
           <<','<<sum.covered/sum.samples<<','<<sum.width/sum.samples<<','<<sum.predict_us/sum.samples
           <<','<<ratio(sum.update_us,sum.observations)<<','<<(sum.predict_us+sum.update_us)/1e6
           <<','<<ratio(sum.ess_sum,sum.ess_count)<<','<<sum.ot_updates<<','<<ratio(sum.ot_failed,sum.ot_updates)
           <<','<<sum.residual_max<<','<<sum.correction_max<<','<<ratio(sum.iterations,sum.ot_updates)<<'\n';
    }
    atomic_text(output,out.str());
}
}
