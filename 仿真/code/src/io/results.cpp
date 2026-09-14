#include "pf/io.hpp"

namespace pf {
// 每条轨迹单独存档, 最后才提交摘要; 进程中断不会产生伪成功的检查点。
void save_run(const fs::path& path,const RunRecord& run) {
  Writer w(path.string()+".partial");w.text("PF_RUN_V1");
  w.text(run.environment);w.text(run.variant);w.text(run.data_hash);w.integer(run.trajectory);
  w.text(run.config.algorithm);w.integer(run.config.particles);w.integer(run.config.seed);
  w.real(run.config.transport.tolerance);w.integer(run.config.transport.max_iterations);
  w.real(run.initialization_ms);w.integer(run.failure_k);w.text(run.failure);w.integer(run.steps.size());
  for(const auto& s:run.steps) {
    w.integer(s.k);w.real(s.elapsed_ms);w.matrix(s.mean);w.matrix(s.weights);w.matrix(s.predicted);w.matrix(s.posterior);
    w.real(s.transport.objective);w.real(s.transport.marginal_residual);w.real(s.transport.negative_mass);w.real(s.transport.dual_gap);
  }
  w.close();commit_file(path.string()+".partial",path);
}
RunRecord load_run(const fs::path& path) {
  verify_file(path);Reader r(path);require(r.text()=="PF_RUN_V1","不支持的滤波结果格式");
  RunRecord run;run.environment=r.text();run.variant=r.text();run.data_hash=r.text();run.trajectory=r.integer(100000);
  run.config.algorithm=r.text();run.config.particles=r.integer(10000000);run.config.seed=r.integer();
  run.config.transport.tolerance=r.real();run.config.transport.max_iterations=r.integer();
  run.initialization_ms=r.real();run.failure_k=r.integer(100000);run.failure=r.text();
  const auto count=r.integer(100000);
  for(std::uint64_t i=0;i<count;++i) {
    FilterStep s;s.k=r.integer(100000);s.elapsed_ms=r.real();s.mean=r.vector();s.weights=r.vector();s.predicted=r.matrix();s.posterior=r.matrix();
    s.transport.objective=r.real();s.transport.marginal_residual=r.real();s.transport.negative_mass=r.real();s.transport.dual_gap=r.real();
    run.steps.push_back(std::move(s));
  }
  r.end();return run;
}
void save_reference(const fs::path& path,const ReferenceRecord& ref) {
  Writer w(path.string()+".partial");w.text("PF_REF_V1");w.text(ref.environment);w.text(ref.variant);w.text(ref.data_hash);
  w.integer(ref.trajectory);w.text(ref.method);w.integer(ref.validated);w.real(ref.mean_precision);w.real(ref.covariance_precision);
  w.integer(ref.steps.size());
  for(const auto& s:ref.steps) { w.integer(s.k);w.matrix(s.mean);w.matrix(s.covariance); }
  w.close();commit_file(path.string()+".partial",path);
}
ReferenceRecord load_reference(const fs::path& path) {
  verify_file(path);Reader r(path);require(r.text()=="PF_REF_V1","不支持的参考格式");
  ReferenceRecord ref;ref.environment=r.text();ref.variant=r.text();ref.data_hash=r.text();ref.trajectory=r.integer(100000);
  ref.method=r.text();ref.validated=r.integer(1);ref.mean_precision=r.real();ref.covariance_precision=r.real();
  const auto count=r.integer(100000);
  for(std::uint64_t i=0;i<count;++i) { ReferenceStep s;s.k=r.integer(100000);s.mean=r.vector();s.covariance=r.matrix();ref.steps.push_back(std::move(s)); }
  r.end();return ref;
}
} // namespace pf
