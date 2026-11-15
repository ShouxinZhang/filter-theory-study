#pragma once
#include "baseline/types.hpp"
#include <Eigen/Dense>
namespace baseline {
struct TransportResult {
    std::vector<double> particles;
    Diagnostics diagnostics;
    Eigen::MatrixXd plan;
};
// 一维平方代价，单调 LP 对偶仅作初值，最终目标仍为指定 epsilon 的熵正则 OT
TransportResult sinkhorn_transform(const std::vector<double>& x,const std::vector<double>& weights,
                                  double epsilon,double tolerance,int max_iterations);
}
