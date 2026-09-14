#include "test.hpp"
#include "pf/filter.hpp"

namespace test {
static pf::Matrix barycenter(const pf::Matrix& x,const pf::TransportPlan& plan) {
  pf::Matrix output=pf::Matrix::Zero(x.rows(),x.cols());
  for(const auto& m:plan.masses)output.col(m.target)+=x.cols()*m.value*x.col(m.source);
  return output;
}
void transport() {
  pf::TransportConfig c;pf::Matrix x(1,2);x<<0,2;pf::Vector w(2);w<<0.75,0.25;
  auto mono=pf::monotone_transport(x,w,c);auto network=pf::network_transport(x,w,c);
  near(mono.diagnostics.objective,1,1e-13,"一维已知最优值");near(network.diagnostics.objective,1,1e-13,"网络单纯形已知最优值");
  auto out=barycenter(x,mono);near(out(0,0),0,1e-14,"重心 0");near(out(0,1),1,1e-14,"重心 1");
  pf::Matrix square(2,4);square<<0,1,0,1,0,0,1,1;pf::Vector diagonal(4);diagonal<<0.5,0,0,0.5;
  auto plan=pf::network_transport(square,diagonal,c);
  near(plan.diagnostics.objective,0.5,1e-12,"二维方形已知最优值与零权重");
  near((barycenter(square,plan).rowwise().mean()-square*diagonal).norm(),0,1e-12,"二维 ETPF 均值守恒");
  pf::Random rng(31);
  for(int n:{1,2,5,20,64})for(int repeat=0;repeat<4;++repeat) {
    pf::Matrix points(1,n);pf::Vector weights(n);
    for(int i=0;i<n;++i) { points(0,i)=rng.normal();weights[i]=i%3==0?0:rng.uniform(); }
    if(weights.sum()==0)weights[0]=1;
    weights/=weights.sum();
    const auto a=pf::monotone_transport(points,weights,c),b=pf::network_transport(points,weights,c);
    near(a.diagnostics.objective,b.diagnostics.objective,1e-9,"两个独立输运算法交叉核查");
    near((barycenter(points,b).rowwise().mean()-points*weights).norm(),0,1e-10,"随机权重均值守恒");
  }
  auto flat=pf::network_transport(pf::Matrix::Zero(4,10),pf::Vector::Constant(10,0.1),c);
  near(flat.diagnostics.objective,0,0,"重复位置退化代价");
  throws([&]{pf::network_transport(x,pf::Vector::Zero(2),c);},"零总权重不可求解");
  pf::Random resampling(5);pf::Matrix ancestors(1,3);ancestors<<1,2,3;pf::Vector only(3);only<<0,1,0;
  near((pf::multinomial_resample(ancestors,only,resampling).array()-2).abs().sum(),0,0,"零权重不能被重采样");
}
} // namespace test
