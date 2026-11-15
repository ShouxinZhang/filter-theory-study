#include "baseline/density.hpp"
#include <cmath>
#include <numeric>
#include <stdexcept>
namespace baseline {
double gaussian_density(double x, double mean, double variance) {
    if (!(variance > 0) || !std::isfinite(variance)) throw std::invalid_argument("高斯方差必须为有限正值");
    return std::exp(-0.5 * (x - mean) * (x - mean) / variance) / std::sqrt(2 * std::acos(-1.0) * variance);
}
GaussianKde::GaussianKde(const std::vector<double>& values): samples(values) {
    if (samples.size() < 2) throw std::invalid_argument("KDE至少需要两个粒子");
    for (double x : samples) if (!std::isfinite(x)) throw std::invalid_argument("KDE粒子非有限");
    sample_mean = std::accumulate(samples.begin(), samples.end(), 0.0) / samples.size();
    sample_variance = 0;
    for (double x : samples) sample_variance += (x-sample_mean)*(x-sample_mean);
    sample_variance /= samples.size()-1;
    if (!(sample_variance > 0)) throw std::invalid_argument("粒子退化为同一点，Scott带宽为零");
    bandwidth = std::sqrt(sample_variance) * std::pow(static_cast<double>(samples.size()), -0.2);
}
double GaussianKde::density(double x) const {
    double sum = 0;
    for (double center : samples) sum += gaussian_density(x, center, bandwidth*bandwidth);
    return sum/samples.size();
}
}
