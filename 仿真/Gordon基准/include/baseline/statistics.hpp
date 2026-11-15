#pragma once
#include "baseline/types.hpp"
namespace baseline {
// 经验分布使用等尾分位点，Gaussian 区间单独计算
Estimate empirical(const std::vector<double>& x,const std::vector<double>& weights={});
Estimate gaussian_estimate(double mean,double variance);
std::vector<double> likelihood_weights(const std::vector<double>& predictions,double y,double variance);
}
