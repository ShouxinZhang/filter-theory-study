#include "baseline/grid_reference.hpp"
#include <Eigen/Dense>
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace baseline {
GridReference grid_reference(const Model& model,
    const std::vector<std::vector<Observation>>& observations,
    double bound, double spacing, int interval) {
    if (!(bound > 0 && spacing > 0) || interval < 1 || observations.empty())
        throw std::invalid_argument("网格与观测参数不合法");
    const int n = static_cast<int>(std::llround(2 * bound / spacing)) + 1;
    if (n < 3 || std::abs((n - 1) * spacing - 2 * bound) > 1e-8)
        throw std::invalid_argument("网格必须覆盖对称区间且均匀划分");
    const int trials = observations.size(), steps = observations.front().size();
    for (const auto& series : observations) {
        if (series.size() != static_cast<size_t>(steps) || series.empty())
            throw std::invalid_argument("轨迹长度不一致");
        for (int k = 0; k < steps; ++k)
            if (series[k].step != k + 1 || !std::isfinite(series[k].value))
                throw std::invalid_argument("观测时间步或数值不合法");
    }
    Eigen::VectorXd x(n), h(n), initial(n), quadrature(n);
    for (int i = 0; i < n; ++i) {
        x[i] = -bound + i * spacing;
        h[i] = model.observation(x[i]);
        quadrature[i] = spacing * ((i == 0 || i == n - 1) ? 0.5 : 1);
        initial[i] = quadrature[i] * std::exp(-std::pow(x[i] - model.initial_mean, 2) / (2 * model.initial_variance));
    }
    initial /= initial.sum();
    Eigen::MatrixXd mass = initial.replicate(1, trials), transition(n, n);
    GridReference result; result.records.resize(trials);
    const double scale = 1 / std::sqrt(2 * std::acos(-1.0) * model.q);
    auto estimate = [&](const Eigen::VectorXd& p) {
        Estimate e; e.mean = x.dot(p);
        e.variance = ((x.array() - e.mean).square() * p.array()).sum();
        double cumulative = 0; e.low = x[n - 1]; e.high = x[n - 1];
        bool low_found = false;
        for (int i = 0; i < n; ++i) {
            cumulative += p[i];
            if (!low_found && cumulative >= 0.025) { e.low = x[i]; low_found = true; }
            if (cumulative >= 0.975) { e.high = x[i]; break; }
        }
        return e;
    };
    for (int k = 1; k <= steps; ++k) {
        // 不按列归一化转移核，先记录真实积分质量损失，再归一化预测分布。
        for (int j = 0; j < n; ++j) {
            double location = model.transition(x[j], k);
            transition.col(j) = (-(x.array() - location).square() / (2 * model.q)).exp()
                * quadrature.array() * scale;
        }
        mass = (transition * mass).eval();
        for (int b = 0; b < trials; ++b) {
            const double total = mass.col(b).sum();
            if (!(total > 0) || !std::isfinite(total)) throw std::runtime_error("预测质量不合法");
            result.max_prediction_mass_error = std::max(result.max_prediction_mass_error, std::abs(total - 1));
            mass.col(b) /= total;
            Record row; row.step = k; row.observed = k % interval == 0;
            row.prior = estimate(mass.col(b));
            if (row.observed) {
                Eigen::ArrayXd log_likelihood = -(h.array() - observations[b][k - 1].value).square() / (2 * model.r);
                log_likelihood -= log_likelihood.maxCoeff();
                mass.col(b).array() *= log_likelihood.exp();
                const double normalizer = mass.col(b).sum();
                if (!(normalizer > 0)) throw std::runtime_error("观测似然积分为零");
                mass.col(b) /= normalizer;
            }
            row.posterior = estimate(mass.col(b));
            result.records[b].push_back(row);
        }
    }
    return result;
}
}
