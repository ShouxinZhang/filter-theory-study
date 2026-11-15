#pragma once
#include <string>
namespace baseline {
// 状态和测量使用独立加性高斯噪声，模型由所有算法共享
struct Model {
    std::string name;
    double q, r, initial_mean = 0, initial_variance = 2;
    explicit Model(const std::string& name);
    double transition(double x, int step) const;
    double transition_derivative(double x) const;
    double observation(double x) const;
    double observation_derivative(double x) const;
};
}
