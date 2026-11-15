#include "baseline/cli.hpp"
#include "baseline/evaluation.hpp"
#include "baseline/io.hpp"
#include <iostream>
// 只读真值与滤波记录，无模型或滤波器调用
int main(int argc,char**argv) {
    try {
        baseline::Args a(argc,argv);
        auto metrics=baseline::evaluate(baseline::read_truth(a.require("truth")),
            baseline::read_records(a.require("filter")),a.integer("common-interval",8));
        baseline::write_metrics(a.require("output"),metrics);
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
