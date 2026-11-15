#pragma once
#include "baseline/types.hpp"
#include <filesystem>
namespace baseline {
// 每个时刻先跨独立轨迹累积平方误差，最后开方
struct TimeSeriesPoint {
    int step=0, observed=0, trials=0;
    double rmse=0, prior_rmse=0, cumulative_rmse=0;
};
class TimeSeriesAccumulator {
    struct Sum { int step=0, observed=0, trials=0; double posterior=0, prior=0; };
    std::vector<Sum> sums;
public:
    void add(const std::vector<Truth>& truth,const std::vector<Record>& records);
    std::vector<TimeSeriesPoint> result()const;
};
void summarize_time_series(const std::filesystem::path& index,const std::filesystem::path& output);
}
