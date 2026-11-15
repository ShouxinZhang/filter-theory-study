#include "baseline/cli.hpp"
#include "baseline/io.hpp"
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <iostream>
#include <sstream>
// 事后评价同时记录经验平方误差和条件后验方差，二者不能混为确定下界。
int main(int argc, char** argv) {
    try {
        using namespace baseline; Args args(argc, argv);
        std::ifstream in(args.require("index")); std::string line;
        if (!std::getline(in, line) || line != "truth_path,filter_path") throw std::runtime_error("索引表头错误");
        std::ostringstream out; out << std::setprecision(17) << "trial,samples,squared_error,truth_squared,posterior_variance,rmse,nrmse,conditional_risk_root,conditional_risk_ratio\n";
        int b = 0; size_t count = 0; double error = 0, truth2 = 0, variance = 0;
        std::vector<double> variance_sums, truth_sums; size_t trial_length = 0;
        auto write = [&](int trial, size_t n, double e, double x, double v) {
            if (!n || !(x > 0)) throw std::runtime_error("评价数据为空或归一化分母为零");
            out << trial << ',' << n << ',' << e << ',' << x << ',' << v << ',' << std::sqrt(e/n)
                << ',' << std::sqrt(e/x) << ',' << std::sqrt(v/n) << ',' << std::sqrt(v/x) << '\n';
        };
        while (std::getline(in, line)) {
            auto fields = split(line); if(fields.size()!=2)throw std::runtime_error("索引列数错误");
            auto truth = read_truth(fields[0]); auto records = read_records(fields[1]);
            if (truth.size() != records.size()) throw std::runtime_error("评价长度不匹配");
            double e = 0, x = 0, v = 0;
            for (size_t k = 0; k < truth.size(); ++k) {
                if (truth[k].step != records[k].step) throw std::runtime_error("评价时间步不匹配");
                e += std::pow(records[k].posterior.mean - truth[k].value, 2);
                x += std::pow(truth[k].value, 2); v += records[k].posterior.variance;
            }
            if (trial_length && trial_length != truth.size()) throw std::runtime_error("轨迹长度须相同以估计置信区间");
            trial_length = truth.size(); variance_sums.push_back(v); truth_sums.push_back(x);
            write(b++, truth.size(), e, x, v); count += truth.size(); error += e; truth2 += x; variance += v;
        }
        write(-1, count, error, truth2, variance);
        atomic_text(args.require("output"), out.str());
        // 以独立轨迹为单位做 delta-method，不能把有时间相关的每一步当作独立样本。
        if (b > 1) {
            double mean_v = variance / b, mean_x = truth2 / b, ratio2 = variance / truth2;
            double v_ss = 0, ratio_ss = 0;
            for (int i = 0; i < b; ++i) {
                v_ss += std::pow(variance_sums[i] - mean_v, 2);
                ratio_ss += std::pow(variance_sums[i] - ratio2 * truth_sums[i], 2);
            }
            double root = std::sqrt(variance/count), relative = std::sqrt(ratio2);
            double root_se = std::sqrt(v_ss / (b * (b - 1.0))) / (2 * trial_length * root);
            double relative_se = std::sqrt(ratio_ss / (b * (b - 1.0))) / (2 * relative * mean_x);
            std::ostringstream ci; ci << std::setprecision(17)
                << "trials,steps,risk_root,risk_root_se,risk_root_ci_low,risk_root_ci_high,relative_risk,relative_se,relative_ci_low,relative_ci_high\n"
                << b << ',' << trial_length << ',' << root << ',' << root_se << ',' << std::max(0.0,root-1.96*root_se) << ',' << root+1.96*root_se
                << ',' << relative << ',' << relative_se << ',' << std::max(0.0,relative-1.96*relative_se) << ',' << relative+1.96*relative_se << '\n';
            atomic_text(args.require("output") + ".ci.csv", ci.str());
        }
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
