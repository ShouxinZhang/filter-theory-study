#include "baseline/filter.hpp"
#include "baseline/statistics.hpp"
#include "baseline/sinkhorn.hpp"
#include <numeric>
#include <cmath>
#include <stdexcept>
namespace baseline {
ParticleFilter::ParticleFilter(const Model& m,const FilterConfig& c,const std::string& a,uint64_t seed)
:model(m),config(c),algorithm(a),x(c.n>=2?c.n:0),process(split_seed(seed,11)),update_rng(split_seed(seed,12)) {
    if(c.n<2)throw std::invalid_argument("粒子数至少为2");
    Random initial(split_seed(seed,10));
    for(auto& value:x)value=m.initial_mean+std::sqrt(m.initial_variance)*initial.gaussian();
    current=empirical(x);
}
void ParticleFilter::predict(int k) {
    for(auto& value:x)value=model.transition(value,k)+std::sqrt(model.q)*process.gaussian();
    current=empirical(x);last={};
}
void ParticleFilter::update(double y) {
    std::vector<double> h(x.size());
    for(size_t i=0;i<x.size();++i)h[i]=model.observation(x[i]);
    if(algorithm=="enkf") {
        double hm=std::accumulate(h.begin(),h.end(),0.0)/h.size(),cov=0,var=0;
        for(size_t i=0;i<x.size();++i){cov+=(x[i]-current.mean)*(h[i]-hm);var+=std::pow(h[i]-hm,2);}
        cov/=x.size()-1;var/=x.size()-1;
        double gain=cov/(var+model.r);
        for(size_t i=0;i<x.size();++i)x[i]+=gain*(y+std::sqrt(model.r)*update_rng.gaussian()-h[i]);
        current=empirical(x);return;
    }
    auto w=likelihood_weights(h,y,model.r);current=empirical(x,w);
    double sq=0;for(double a:w)sq+=a*a;last.ess=1/sq;
    if(algorithm=="bpf") {
        std::vector<double> next(x.size());size_t j=0;double sum=w[0],u=update_rng.uniform()/x.size();
        for(size_t i=0;i<x.size();++i) {
            double point=u+static_cast<double>(i)/x.size();
            while(point>sum&&j+1<x.size())sum+=w[++j];
            next[i]=x[j];
        }
        x=std::move(next);
    } else {
        auto result=sinkhorn_transform(x,w,config.epsilon,config.tolerance,config.max_iterations);
        double ess=last.ess;last=result.diagnostics;last.ess=ess;x=std::move(result.particles);
    }
}
}
