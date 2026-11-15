#pragma once
#include "baseline/model.hpp"
#include "baseline/types.hpp"
#include <vector>
namespace baseline {
// 均匀网格上的概率质量积分，批处理只共享转移矩阵，各轨迹后验独立。
struct GridReference {
    std::vector<std::vector<Record>> records;
    double max_prediction_mass_error = 0;
};
GridReference grid_reference(const Model& model,
    const std::vector<std::vector<Observation>>& observations,
    double bound, double spacing, int interval);
}
