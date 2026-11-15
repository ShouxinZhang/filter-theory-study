#pragma once
#include <vector>
namespace baseline {
// 一维等权Gaussian KDE，Scott带宽采用样本标准差，不读取真值调参。
class GaussianKde {
    std::vector<double> samples;
public:
    double bandwidth, sample_mean, sample_variance;
    explicit GaussianKde(const std::vector<double>& values);
    double density(double x) const;
};
double gaussian_density(double x, double mean, double variance);
}
