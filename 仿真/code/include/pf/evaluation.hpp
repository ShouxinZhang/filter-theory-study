#pragma once
#include "pf/dataset.hpp"
#include <limits>

namespace pf {
inline constexpr double missing=std::numeric_limits<double>::quiet_NaN();
struct Metrics {
  std::string group;
  double squared_error=0,absolute_error=0,bayes_mse=0,excess_mse=0;
  double mean_precision=0,covariance_precision=0;
  int components=0,samples=0,reference_samples=0;
};
struct StepMetrics {
  int trajectory=0,k=0;
  std::string group;
  Vector error;
  double squared_error=0,absolute_error=0,ess=0,mean_shift=0,elapsed_ms=0;
  double bayes_mse_ref=missing,excess_mse_ref=missing;
};
struct TrajectoryEvaluation {
  int id=0;
  bool success=false;
  std::string failure;
  double initialization_ms=0;
  std::vector<StepMetrics> steps;
  std::vector<Metrics> metrics;
};
TrajectoryEvaluation evaluate_trajectory(const TruthDataset& truth,const RunRecord& run,const ReferenceRecord* reference=nullptr);
void write_report(const fs::path& directory,const std::vector<TrajectoryEvaluation>& evaluations);
} // namespace pf
