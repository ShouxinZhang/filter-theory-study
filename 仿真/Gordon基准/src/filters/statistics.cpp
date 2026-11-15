#include "baseline/statistics.hpp"
#include <algorithm>
#include <numeric>
#include <cmath>
#include <stdexcept>
namespace baseline {
Estimate gaussian_estimate(double m,double p) {
    if(!std::isfinite(m)||!std::isfinite(p)||p<0)throw std::runtime_error("高斯状态无效");
    double r=1.959963984540054*std::sqrt(p);
    return {m,p,m-r,m+r};
}
Estimate empirical(const std::vector<double>& x,const std::vector<double>& w) {
    if(x.empty()||(!w.empty()&&w.size()!=x.size()))throw std::invalid_argument("粒子维度错误");
    Estimate e; std::vector<std::pair<double,double>> sorted; sorted.reserve(x.size());
    double uniform=1.0/x.size(), mass=0;
    for(size_t i=0;i<x.size();++i) {
        double wi=w.empty()?uniform:w[i];
        if(!std::isfinite(x[i])||!std::isfinite(wi)||wi<0)throw std::runtime_error("非有限粒子或权重");
        mass+=wi; e.mean+=wi*x[i]; sorted.emplace_back(x[i],wi);
    }
    if(std::abs(mass-1)>1e-9)throw std::runtime_error("权重未归一化");
    for(size_t i=0;i<x.size();++i)e.variance+=(w.empty()?uniform:w[i])*std::pow(x[i]-e.mean,2);
    std::sort(sorted.begin(),sorted.end()); double sum=0; e.low=sorted.back().first; e.high=e.low;
    bool found=false;
    for(auto [value,weight]:sorted) {
        sum+=weight;
        if(!found && sum>=0.025){e.low=value; found=true;}
        if(sum>=0.975){e.high=value; break;}
    }
    return e;
}
std::vector<double> likelihood_weights(const std::vector<double>& h,double y,double r) {
    std::vector<double>w(h.size()); double best=-INFINITY;
    for(size_t i=0;i<h.size();++i){w[i]=-0.5*std::pow(y-h[i],2)/r; best=std::max(best,w[i]);}
    if(!std::isfinite(best))throw std::runtime_error("所有似然都非有限");
    double total=0;
    for(auto& z:w){z=std::exp(z-best);total+=z;}
    for(auto& z:w)z/=total;
    return w;
}
}
