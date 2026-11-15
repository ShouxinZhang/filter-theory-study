#include "baseline/cli.hpp"
#include "baseline/time_series.hpp"
#include <iostream>
// 独立后处理入口，只读取已保存的真值和滤波输出，不重新执行滤波
int main(int argc,char**argv) {
    try {
        baseline::Args a(argc,argv);
        baseline::summarize_time_series(a.require("index"),a.require("output"));
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
