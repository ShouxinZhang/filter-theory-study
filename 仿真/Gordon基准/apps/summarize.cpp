#include "baseline/cli.hpp"
#include "baseline/evaluation.hpp"
#include <iostream>
// C++ 聚合和轨迹级 bootstrap，绘图脚本只消费结果
int main(int argc,char**argv) {
    try {
        baseline::Args a(argc,argv);
        baseline::summarize(a.require("index"),a.require("output"),a.integer("bootstrap",1000));
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
