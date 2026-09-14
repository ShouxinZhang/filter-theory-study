#include "test.hpp"
int main() {
  try {
    test::models();std::cout<<"环境, 随机数与初始化通过\n";
    test::noise();std::cout<<"噪声分布, 参数恢复与算法接入通过\n";
    test::transport();std::cout<<"输运约束, 全局最优值与均值守恒通过\n";
    test::integration();std::cout<<"因果性, 存储与独立评估通过\n";
    test::reference();std::cout<<"网格参考与独立重要性积分交叉核查通过\n";
  } catch(const std::exception& e) { std::cerr<<e.what()<<'\n';return 1; }
}
