#pragma once
#include "baseline/model.hpp"
#include "baseline/types.hpp"
#include "baseline/random.hpp"
#include <memory>
namespace baseline {
// 接口只接收当前时刻信息，无法获取真实状态
class Filter {
public:
    virtual ~Filter()=default;
    virtual void predict(int step)=0;
    virtual void update(double observation)=0;
    virtual Estimate estimate() const=0;
    virtual Diagnostics diagnostics() const {return {};}
    virtual std::vector<double> particles() const {return {};}
};
class GaussianFilter final:public Filter {
    Model model; double mean,variance;
public:
    explicit GaussianFilter(const Model&);
    void predict(int)override;
    void update(double)override;
    Estimate estimate()const override;
};
class ParticleFilter final:public Filter {
    Model model; FilterConfig config; std::string algorithm;
    std::vector<double> x; Random process,update_rng;
    Estimate current; Diagnostics last;
public:
    ParticleFilter(const Model&,const FilterConfig&,const std::string&,uint64_t);
    void predict(int)override;
    void update(double)override;
    Estimate estimate()const override{return current;}
    Diagnostics diagnostics()const override{return last;}
    std::vector<double> particles()const override{return x;}
};
std::unique_ptr<Filter> make_filter(const Model&,const FilterConfig&,const std::string&,uint64_t);
}
