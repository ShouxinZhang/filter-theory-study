#include "test.hpp"
#include "pf/environment.hpp"
#include "pf/filter.hpp"
#include <numbers>

namespace test {
void noise() {
  pf::Vector mean(3),sd(3);mean<<-2,0,3;sd<<0.5,1,2;
  const auto normal=pf::Noise::normal(mean,sd);
  pf::Random rng(41);pf::Vector value(3),sum=pf::Vector::Zero(3),squares=sum;
  for(int i=0;i<100000;++i) { normal.sample(value,rng);sum+=value;squares+=value.array().square().matrix(); }
  for(int j=0;j<3;++j) {
    near(sum[j]/100000,mean[j],0.03,"逐维正态均值");
    near(squares[j]/100000-std::pow(sum[j]/100000,2),sd[j]*sd[j],0.07,"逐维正态方差");
  }
  near(normal.log_density(mean),-1.5*std::log(2*std::numbers::pi),1e-14,"正态联合对数密度");
  pf::Vector lower(2),upper(2);lower<<-2,10;upper<<4,12;
  const auto uniform=pf::Noise::uniform(lower,upper);value.resize(2);sum=pf::Vector::Zero(2);squares=sum;
  for(int i=0;i<100000;++i) {
    uniform.sample(value,rng);check((value.array()>=lower.array()).all()&&(value.array()<=upper.array()).all(),"均匀支持集");
    sum+=value;squares+=value.array().square().matrix();
  }
  near(sum[0]/100000,1,0.03,"均匀第一维均值");near(sum[1]/100000,11,0.01,"均匀第二维均值");
  near(squares[0]/100000-std::pow(sum[0]/100000,2),3,0.04,"均匀方差");
  near(uniform.log_density(lower),-std::log(12),1e-14,"均匀联合密度与边界");
  value<<-3,11;check(uniform.log_density(value)==-INFINITY,"支持集外为零密度");
  pf::Vector points(5),logs(5);points<<-INFINITY,-2,0,2,INFINITY;
  for(const auto& distribution:{pf::Noise::normal(1,1,2),pf::Noise::uniform(1,-1,1)}) {
    distribution.log_density_scalar_batch(points,logs);
    for(int j=0;j<points.size();++j) {
      const double expected=distribution.log_density_scalar(points[j]);
      if(std::isfinite(expected))near(logs[j],expected,1e-14,"批量密度与标量密度一致");
      else check(logs[j]==expected,"批量密度支持集与无穷输入");
    }
  }
  for(const auto& distribution:{normal,uniform}) {
    const auto restored=pf::Noise::decode(distribution.encode());
    check(restored.encode()==distribution.encode(),"噪声参数序列化往返");
    pf::Random a(29),b(29);pf::Vector x(distribution.dimension()),y(x.size());
    distribution.sample(x,a);restored.sample(y,b);near((x-y).norm(),0,0,"恢复配置后样本可复现");
  }
  throws([]{pf::Noise::normal(0);},"拒绝零维噪声");
  throws([]{pf::Noise::normal(2,0,0);},"拒绝零标准差");
  throws([]{pf::Noise::uniform(2,2,2);},"拒绝零宽度区间");
  throws([]{pf::Noise::normal(pf::Vector::Zero(2),pf::Vector::Ones(3));},"拒绝参数数组维度不一致");
  throws([]{pf::Noise::decode("uniform 2 0 1 2");},"拒绝不完整序列化参数");
  throws([&]{normal.log_density(pf::Vector::Zero(1));},"拒绝密度输入维度错误");
  pf::EnvironmentNoise config;config.process=pf::Noise::uniform(1,0.2,0.8);config.observation=pf::Noise::uniform(1,-1000000,1000000);
  auto model=pf::make_environment("gordon",config);
  auto restored=pf::environment_from_parameters(model->name(),model->parameters());
  check(restored->parameters()==model->parameters(),"环境自动恢复冻结噪声");
  for(const std::string algorithm:{"bpf","etpf"}) {
    pf::FilterConfig c;c.algorithm=algorithm;c.particles=64;
    pf::ParticleFilter filter(*restored,c,0);const auto step=filter.step(1,0);
    near((step.weights.array()-1.0/64).abs().maxCoeff(),0,0,"均匀观测似然接入两种算法");
    pf::Random initial(pf::seed_for(c.seed,0,10));pf::Vector prior(1);
    for(int i=0;i<c.particles;++i) {
      restored->sample_initial(prior,initial);const double residual=step.predicted(0,i)-pf::gordon_drift(1,prior[0]);
      check(residual>=0.2-1e-14&&residual<=0.8+1e-14,"粒子传播使用配置后的均匀噪声");
    }
    throws([&]{filter.step(2,1e20);},"支持集不覆盖观测时必须明确失败");
  }
  config.process=pf::Noise::normal(3);
  throws([&]{pf::make_environment("tracking",config);},"追踪入口拒绝三维过程噪声");
}
} // namespace test
