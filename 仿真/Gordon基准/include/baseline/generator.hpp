#pragma once
#include "baseline/model.hpp"
#include <filesystem>
#include <cstdint>
namespace baseline {
// 真值与观测分别写盘，filter 可执行程序不接收真值路径
void generate(const Model&,int steps,uint64_t seed,const std::filesystem::path& observations,
              const std::filesystem::path& truth,bool fixed_initial=false);
}
