#include "test.hpp"
#include "pf/reference.hpp"
#include "pf/environment.hpp"

namespace test {
void reference() {
  pf::PublicDataset data;data.environment="gordon-v1";data.variant="fixed";data.hash="test";
  pf::Observations observation;observation.values={3};
  const auto ref=pf::grid_reference(data,observation,{0.125,40,1e-5});
  check(ref.validated,"充分细化的一维网格参考应通过验证");
  // 从连续先验和转移直接抽样, 提供独立于网格递推的首步积分检查。
  auto model=pf::make_environment(data.environment);pf::Random initial(481),process(917);
  pf::Vector x(1),next(1);double sum=0,mean=0,second=0;
  for(int i=0;i<300000;++i) {
    model->sample_initial(x,initial);model->propagate(1,x,next,process);
    const double w=std::exp(model->log_likelihood(3,next));
    sum+=w;mean+=w*next[0];second+=w*next[0]*next[0];
  }
  mean/=sum;second=second/sum-mean*mean;
  near(ref.steps[0].mean[0],mean,0.15,"参考均值与独立蒙特卡洛积分");
  near(ref.steps[0].covariance(0,0),second,0.5,"参考协方差与独立蒙特卡洛积分");
  const auto coarse=pf::grid_reference(data,observation,{4,40,1e-8});
  check(!coarse.validated,"过粗参考网格不能自动通过验证");
  check(pf::grid_method({0.125,64,1e-9})!=pf::grid_method({0.125,64,2e-9}),"参考续跑键保留小数精度");
}
} // namespace test
