#include "test.hpp"
#include "pf/environment.hpp"
#include "pf/filter.hpp"
#include <numbers>

namespace test {
void models() {
  pf::Random rng(123);double sum=0,squares=0;
  for(int i=0;i<100000;++i) { const auto v=rng.normal();sum+=v;squares+=v*v; }
  near(sum/100000,0,0.012,"正态均值");near(squares/100000,1,0.025,"正态方差");
  check(pf::seed_for(1,0,0)!=pf::seed_for(1,0,1),"随机流分离");
  near(pf::gordon_drift(1,0),8,1e-14,"Gordon 相位索引");
  auto g=pf::make_environment("gordon");pf::Vector x(1),next(1);x[0]=0.1;
  pf::Random a(9),b(9);g->propagate(1,x,next,a);
  near(next[0],0.05+2.5/1.01+8+std::sqrt(10.0)*b.normal(),1e-13,"Gordon 过程噪声标准差");
  near(g->log_likelihood(0,pf::Vector::Zero(1)),-0.5*std::log(2*std::numbers::pi),1e-14,"Gordon 似然常数");
  auto t=pf::make_environment("tracking");pf::Vector p(4),q(4);p<<-0.05,0.001,0.7,-0.055;
  pf::Random r(2);t->propagate(2,p,q,r);
  near(q[0]-p[0]-p[1],0.5*(q[1]-p[1]),1e-15,"追踪 x 方向秩二噪声");
  near(q[2]-p[2]-p[3],0.5*(q[3]-p[3]),1e-15,"追踪 y 方向秩二噪声");
  near(pf::tracking_bearing(p),std::atan(-14.0),1e-14,"主值 atan 而非 atan2");
  throws([&]{t->propagate(1,p,q,r);},"追踪首步不允许传播");
  pf::FilterConfig c;c.particles=64;c.seed=87;pf::ParticleFilter f(*t,c,3);
  auto step=f.step(1,-1.5);pf::Random initial(pf::seed_for(c.seed,3,10));
  for(int i=0;i<c.particles;++i) { t->sample_initial(q,initial);near((q-step.predicted.col(i)).norm(),0,0,"追踪首步直接使用先验"); }
  pf::Vector logs(3);logs<<-10000,-10001,-INFINITY;const auto w=pf::normalized_log_weights(logs);
  near(w.sum(),1,1e-15,"log-sum-exp 归一化");near(w[0]/w[1],std::exp(1),1e-13,"极小似然相对权重");
  throws([&]{pf::normalized_log_weights(pf::Vector::Constant(2,-INFINITY));},"全部零似然必须失败");
}
} // namespace test
