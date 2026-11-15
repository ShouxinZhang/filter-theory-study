#include "baseline/density.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
int main() {
    try {
        baseline::GaussianKde kde({-1,1});double bandwidth=std::sqrt(2)*std::pow(2,-0.2);
        if(std::abs(kde.bandwidth-bandwidth)>1e-12)throw std::runtime_error("Scott带宽错误");
        double expected=std::exp(-1/(2*bandwidth*bandwidth))/(bandwidth*std::sqrt(2*std::acos(-1.0)));
        if(std::abs(kde.density(0)-expected)>1e-12)throw std::runtime_error("核混合密度错误");
        if(std::abs(kde.density(2)-kde.density(-2))>1e-12)throw std::runtime_error("对称性错误");
        double integral=0;
        for(int i=0;i<=20000;++i)integral+=kde.density(-10+i*0.001)*0.001*((i==0||i==20000)?0.5:1);
        if(std::abs(integral-1)>1e-8)throw std::runtime_error("KDE归一化错误");
        bool rejected=false;try{baseline::GaussianKde degenerate({1,1});}catch(const std::invalid_argument&){rejected=true;}
        if(!rejected)throw std::runtime_error("应拒绝零带宽");
        std::cout<<"KDE解析密度与积分验证通过\n";
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
