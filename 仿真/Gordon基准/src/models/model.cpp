#include "baseline/model.hpp"
#include <cmath>
#include <stdexcept>
namespace baseline {
Model::Model(const std::string& n): name(n), q(n=="linear"?0.2:10), r(n=="linear"?0.5:1) {
    if(n!="linear" && n!="gordon") throw std::invalid_argument("未知模型: "+n);
}
double Model::transition(double x,int k) const {
    return name=="linear" ? 0.9*x : 0.5*x+25*x/(1+x*x)+8*std::cos(1.2*(k-1));
}
double Model::transition_derivative(double x) const {
    return name=="linear" ? 0.9 : 0.5+25*(1-x*x)/std::pow(1+x*x,2);
}
double Model::observation(double x) const { return name=="linear" ? x : x*x/20; }
double Model::observation_derivative(double x) const { return name=="linear" ? 1 : x/10; }
}
