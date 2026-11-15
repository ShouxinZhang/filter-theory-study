#pragma once
#include <vector>
#include <limits>
namespace baseline {
inline double missing() { return std::numeric_limits<double>::quiet_NaN(); }
struct Estimate { double mean=0, variance=0, low=0, high=0; };
struct Diagnostics {
    double ess=missing(), residual=missing(), correction=missing(), transport_cost=missing();
    int iterations=0, converged=-1;
};
// PF 的后验统计在重采样或位置变换前计算，记录中不含真值
struct Record {
    int step=0, observed=0;
    Estimate prior, posterior;
    double predict_us=0, update_us=0;
    Diagnostics diagnostics;
};
struct Observation { int step; double value; };
struct Truth { int step; double value; };
struct FilterConfig {
    int n=500, max_iterations=2000;
    double epsilon=1, tolerance=1e-8;
};
}
