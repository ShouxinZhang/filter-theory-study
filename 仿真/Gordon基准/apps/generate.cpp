#include "baseline/cli.hpp"
#include "baseline/generator.hpp"
#include <iostream>
// 生成入口只组装配置，具体逻辑在 benchmark 模块
int main(int argc,char** argv) {
    try {
        baseline::Args a(argc,argv);
        baseline::generate(baseline::Model(a.get("model","gordon")),a.integer("steps",400),a.seed(),
                           a.require("observations"),a.require("truth"),a.integer("fixed-initial",0)!=0);
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
