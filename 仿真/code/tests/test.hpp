#pragma once
#include "pf/core.hpp"
#include <functional>
#include <iostream>

namespace test {
// 不使用 assert, 因为 Release 构建也必须执行全部数学断言。
inline void check(bool value,const std::string& label) { pf::require(value,"测试失败: "+label); }
inline void near(double actual,double expected,double tolerance,const std::string& label) {
  check(std::isfinite(actual)&&std::abs(actual-expected)<=tolerance,label+": "+std::to_string(actual)+" vs "+std::to_string(expected));
}
inline void throws(const std::function<void()>& function,const std::string& label) {
  bool caught=false;try { function(); } catch(const std::exception&) { caught=true; }check(caught,label);
}
void models();
void transport();
void integration();
void reference();
} // namespace test
