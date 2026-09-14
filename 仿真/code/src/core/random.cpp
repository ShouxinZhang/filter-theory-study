#include "pf/core.hpp"
#include <cmath>
#include <numbers>

namespace pf {
double Random::uniform() {
  // 取 52 位并移至区间中点, 保证严格处于 (0,1), log 不会接收零。
  return (static_cast<double>(engine_() >> 12) + 0.5) * 0x1.0p-52;
}
double Random::normal() {
  if (spare_ready_) { spare_ready_ = false; return spare_; }
  const double radius = std::sqrt(-2 * std::log(uniform()));
  const double angle = 2 * std::numbers::pi * uniform();
  spare_ = radius * std::sin(angle);
  spare_ready_ = true;
  return radius * std::cos(angle);
}
static std::uint64_t mix(std::uint64_t x) {
  x += 0x9e3779b97f4a7c15ULL;
  x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
  x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
  return x ^ (x >> 31);
}
std::uint64_t seed_for(std::uint64_t base, std::uint64_t trajectory, std::uint64_t stream) {
  return mix(base ^ mix(trajectory) ^ mix(stream + 0x50460000ULL));
}
} // namespace pf
