#pragma once
#include "pf/dataset.hpp"

namespace pf {
struct GridConfig { double spacing=0.125, bound=64, tolerance=1e-5; };
std::string grid_method(const GridConfig& config);
// 三次网格细化, 扩域及错位网格交叉核查, 结果仅是经检查的数值参考。
ReferenceRecord grid_reference(const PublicDataset& data,const Observations& observations,const GridConfig& config);
} // namespace pf
