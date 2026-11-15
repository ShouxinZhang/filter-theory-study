#pragma once
#include <cstdint>
#include <random>
namespace baseline {
// 独立用途流防止重采样消耗改变下一步过程噪声
inline uint64_t split_seed(uint64_t x,uint64_t stream) {
    x += 0x9e3779b97f4a7c15ULL*(stream+1);
    x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;
    x=(x^(x>>27))*0x94d049bb133111ebULL;
    return x^(x>>31);
}
struct Random {
    std::mt19937_64 engine;
    std::normal_distribution<double> normal{0,1};
    explicit Random(uint64_t seed):engine(seed) {}
    double gaussian() { return normal(engine); }
    double uniform() { return std::generate_canonical<double,53>(engine); }
};
}
