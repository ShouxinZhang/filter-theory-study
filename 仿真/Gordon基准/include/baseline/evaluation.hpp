#pragma once
#include "baseline/types.hpp"
#include <filesystem>
namespace baseline {
// 累加平方误差和计数后再开方，不平均单步绝对误差或逐轨迹 RMSE
struct Metrics {
    double samples=0,sse=0,observations=0,pre_sse=0,post_sse=0;
    double common=0,common_pre_sse=0,common_post_sse=0,covered=0,width=0;
    double predict_us=0,update_us=0,ess_sum=0,ess_count=0,ot_updates=0,ot_failed=0;
    double residual_max=0,correction_max=0,iterations=0;
};
Metrics evaluate(const std::vector<Truth>&,const std::vector<Record>&,int common_interval);
void write_metrics(const std::filesystem::path&,const Metrics&);
Metrics read_metrics(const std::filesystem::path&);
void summarize(const std::filesystem::path& index,const std::filesystem::path& output,int bootstrap=1000);
}
