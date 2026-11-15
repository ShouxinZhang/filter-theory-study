#include "baseline/filter.hpp"
#include "baseline/statistics.hpp"
#include <cmath>
#include <stdexcept>
namespace baseline {
GaussianFilter::GaussianFilter(const Model& m):model(m),mean(m.initial_mean),variance(m.initial_variance){}
void GaussianFilter::predict(int k) {
    double f=model.transition_derivative(mean);
    mean=model.transition(mean,k);variance=f*f*variance+model.q;
}
void GaussianFilter::update(double y) {
    double h=model.observation_derivative(mean),gain=variance*h/(h*h*variance+model.r);
    mean+=gain*(y-model.observation(mean));
    // Joseph 形式避免小的负方差，线性模型时就是标准 KF
    variance=std::pow(1-gain*h,2)*variance+gain*gain*model.r;
}
Estimate GaussianFilter::estimate()const{return gaussian_estimate(mean,variance);}
std::unique_ptr<Filter> make_filter(const Model& m,const FilterConfig& c,const std::string& a,uint64_t seed) {
    if(a=="kf"&&m.name!="linear")throw std::invalid_argument("标准 KF 仅用于线性模型，请对 Gordon 使用 ekf");
    if(a=="kf"||a=="ekf")return std::make_unique<GaussianFilter>(m);
    if(a=="bpf"||a=="enkf"||a=="etpf")return std::make_unique<ParticleFilter>(m,c,a,seed);
    throw std::invalid_argument("未知滤波器: "+a);
}
}
