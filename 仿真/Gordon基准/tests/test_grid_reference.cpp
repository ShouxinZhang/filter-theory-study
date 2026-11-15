#include "baseline/grid_reference.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
int main() {
    try {
        using namespace baseline; Model model("linear");
        // 线性高斯解析 KF 为独立校验，同时改变未来观测检查在线性。
        std::vector<std::vector<Observation>> data{{{1,1},{2,-0.4},{3,0.3}},{{1,1},{2,-0.4},{3,8}}};
        for (int interval : {1, 2}) {
            auto result = grid_reference(model, data, 15, 0.05, interval);
            double mean = 0, variance = 2;
            for (int k=1; k<=3; ++k) {
                mean *= 0.9; variance = 0.81*variance+0.2;
                if(k%interval==0) { double gain=variance/(variance+0.5); mean+=gain*(data[0][k-1].value-mean); variance*=1-gain; }
                auto e=result.records[0][k-1].posterior;
                if(std::abs(e.mean-mean)>1e-9 || std::abs(e.variance-variance)>1e-9)
                    throw std::runtime_error("网格与解析KF不一致");
                if(k<3 && std::abs(e.mean-result.records[1][k-1].posterior.mean)>1e-12)
                    throw std::runtime_error("未来观测影响当前结果");
            }
        }
        std::cout<<"网格参考解析校验通过\n";
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
