#include "pf/filter.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <vector>
#include <omp.h>

namespace fs=std::filesystem;
using Real=long double;
constexpr int paths=64,repeats=32,steps=1000,particles=128;
constexpr double observation_variance=.1;
constexpr double process_variance=0;
std::string boundary;
constexpr std::uint64_t seed=202609142122ULL;
enum Metric {BAYES,BIAS,FLUCTUATION,RESAMPLING,CENTROID,PRE_MSE,POST_MSE,
             EMPIRICAL_BAYES,LOCAL_CROSS,BAYES_CROSS,UNIQUE,CONDITIONAL_RESAMPLING,COUNT};
using Record=std::array<Real,COUNT>;
const std::array<std::string,COUNT> metric_names={"bayes_risk","bias_squared_corrected","algorithm_fluctuation",
    "resampling_disturbance","centroid_mse","weighted_state_mse","post_state_mse",
    "empirical_bayes_mse","resampling_cross","bayes_cross","unique_particles","conditional_bpf_resampling"};
struct Moment {
  int n=0;Real mean=0,m2=0;
  void add(Real v){++n;const Real d=v-mean;mean+=d/n;m2+=d*(v-mean);}
  Real variance()const{return m2/(n-1);}
  Real se()const{return std::sqrt(variance()/n);}
};
double drift(double x){return 4*x*(1-x);}
double measurement(double x){return x*x;}
double reflect(double x){return std::abs(std::remainder(x,2));}
double propagate(double x,pf::Random& rng){
  const double u=drift(x);
  for(;;){
    const double v=u+std::sqrt(process_variance)*rng.normal();
    if(boundary=="reflect")return reflect(v);
    if(v>=0&&v<=1)return v;
  }
}

void generate(const fs::path& dir){
  std::ofstream data(dir/"data.csv");data<<std::setprecision(17)<<"trial,step,truth,observation\n";
  for(int b=0;b<paths;++b){
    pf::Random init(pf::seed_for(seed,b,100)),obs(pf::seed_for(seed,b,101)),process(pf::seed_for(seed,b,102));
    double truth=init.uniform();
    for(int k=0;k<steps;++k){truth=propagate(truth,process);const double y=measurement(truth)+std::sqrt(observation_variance)*obs.normal();
      data<<b<<','<<k+1<<','<<truth<<','<<y<<'\n';}
  }
}

struct Filter {
  pf::Matrix x;
  pf::Random resampling,process;
  bool etpf;
  Filter(int b,int rep,bool use_etpf):x(1,particles),
    resampling(pf::seed_for(seed,b*1000000ULL+rep,12)),process(pf::seed_for(seed,b*1000000ULL+rep,11)),etpf(use_etpf){
    pf::Random init(pf::seed_for(seed,b*1000000ULL+rep,10));
    for(int i=0;i<particles;++i)x(0,i)=init.uniform();
  }
  struct Output{double mean,post,delta,marginal;int unique;double conditional_resampling;};
  Output step(double y){
    // Bootstrap propagation, then the existing normalization/resampling/OT primitives.
    for(int i=0;i<particles;++i)x(0,i)=propagate(x(0,i),process);
    pf::Vector logw(particles);
    for(int i=0;i<particles;++i){const double d=y-measurement(x(0,i));logw[i]=-.5*d*d/observation_variance;}
    const auto w=pf::normalized_log_weights(logw);
    const double mean=(x*w)[0];double marginal=0,conditional_resampling=0;
    for(int i=0;i<particles;++i)conditional_resampling+=w[i]*std::pow(x(0,i)-mean,2)/particles;
    if(etpf){
      const auto plan=pf::monotone_transport(x,w,{});
      pf::Matrix posterior=pf::Matrix::Zero(1,particles);
      for(const auto& mass:plan.masses)posterior.col(mass.target).noalias()+=particles*mass.value*x.col(mass.source);
      x=std::move(posterior);marginal=plan.diagnostics.marginal_residual;
    }else x=pf::multinomial_resample(x,w,resampling);
    pf::require(x.minCoeff()>=0&&x.maxCoeff()<=1,"particle outside [0,1]");
    std::vector<double> sorted(x.data(),x.data()+particles);std::sort(sorted.begin(),sorted.end());
    const int unique=std::unique(sorted.begin(),sorted.end())-sorted.begin();
    const double post=x.row(0).mean();return{mean,post,post-mean,marginal,unique,conditional_resampling};
  }
};

std::vector<double> binary(const fs::path& file){
  std::vector<double> x(paths*steps*2);std::ifstream in(file,std::ios::binary);
  in.read(reinterpret_cast<char*>(x.data()),x.size()*sizeof(double));
  pf::require(in.gcount()==static_cast<std::streamsize>(x.size()*sizeof(double)),"reference size mismatch");return x;
}

void calculate(const fs::path& dir){
  std::vector<double> truth(paths*steps),observations(paths*steps);
  std::ifstream data(dir/"data.csv");std::string line;std::getline(data,line);int seen=0;
  while(std::getline(data,line)){
    std::replace(line.begin(),line.end(),',',' ');std::istringstream row(line);int b,k;double t,y;
    row>>b>>k>>t>>y;const int j=b*steps+k-1;truth[j]=t;observations[j]=y;++seen;
  }
  pf::require(seen==paths*steps,"incomplete observations");
  const auto fine=binary(dir/"reference_16384.bin"),coarse=binary(dir/"reference_8192.bin");
  double ref_mean_change=0,ref_variance_change=0;
  for(int j=0;j<paths*steps;++j){
    ref_mean_change=std::max(ref_mean_change,std::abs(fine[2*j]-coarse[2*j]));
    ref_variance_change=std::max(ref_variance_change,std::abs(fine[2*j+1]-coarse[2*j+1]));
  }
  pf::require(ref_mean_change<1e-5 && ref_variance_change<1e-5,"reference refinement failed");
  std::vector<Record> results(paths*2*3),curves(paths*2*steps);
  std::vector<std::array<int,2>> endpoints(paths*2*repeats);
  std::vector<Real> max_delta(paths),max_identity(paths),max_first(paths),max_marginal(paths);
  #pragma omp parallel for schedule(dynamic)
  for(int b=0;b<paths;++b){
    std::vector<double> first(repeats);
    for(int a=0;a<2;++a){
      std::vector<Moment> centers(steps);
      for(int rep=0;rep<repeats;++rep){
        Filter f(b,rep,a==1);
        int first_single=-1;
        for(int k=0;k<steps;++k){
          const auto o=f.step(observations[b*steps+k]);
          if(first_single<0 && o.unique==1)first_single=k+1;
          if(k==steps-1)endpoints[(b*2+a)*repeats+rep]={first_single,o.unique};
          const Real m=fine[2*(b*steps+k)],t=truth[b*steps+k],before=o.mean,after=o.post,delta=o.delta;
          if(k==0){if(a==0)first[rep]=o.mean;else max_first[b]=std::max(max_first[b],std::abs(before-first[rep]));}
          if(a==1)max_delta[b]=std::max(max_delta[b],std::abs(delta));
          max_marginal[b]=std::max(max_marginal[b],Real(o.marginal));
          centers[k].add(before);
          auto& c=curves[(b*2+a)*steps+k];
          c[CENTROID]+=(before-m)*(before-m)/repeats;
          c[RESAMPLING]+=delta*delta/repeats;
          c[CONDITIONAL_RESAMPLING]+=o.conditional_resampling/repeats;
          c[PRE_MSE]+=(before-t)*(before-t)/repeats;
          c[POST_MSE]+=(after-t)*(after-t)/repeats;
          c[LOCAL_CROSS]+=2*(before-m)*delta/repeats;
          c[BAYES_CROSS]+=2*(m-t)*(after-m)/repeats;
          c[UNIQUE]+=Real(o.unique)/repeats;
        }
      }
      for(int k=0;k<steps;++k){
        auto& c=curves[(b*2+a)*steps+k];const Real m=fine[2*(b*steps+k)],t=truth[b*steps+k];
        c[BAYES]=fine[2*(b*steps+k)+1];c[EMPIRICAL_BAYES]=(m-t)*(m-t);
        c[FLUCTUATION]=centers[k].variance();
        c[BIAS]=(centers[k].mean-m)*(centers[k].mean-m)-c[FLUCTUATION]/repeats;
        for(const Real d:{c[CENTROID]-c[BIAS]-c[FLUCTUATION],
            c[POST_MSE]-c[EMPIRICAL_BAYES]-c[CENTROID]-c[RESAMPLING]-c[LOCAL_CROSS]-c[BAYES_CROSS]})
          max_identity[b]=std::max(max_identity[b],std::abs(d));
        for(int st=0;st<3;++st){
          if((st==1&&k>=100)||(st==2&&k<100))continue;
          const int width=st==0?steps:st==1?100:steps-100;
          for(int q=0;q<COUNT;++q)results[(b*2+a)*3+st][q]+=c[q]/width;
        }
      }
    }
  }
  std::ofstream collapse(dir/"collapse.csv");collapse<<"path,algorithm,repeat,first_single_step,final_unique\n";
  for(int b=0;b<paths;++b)for(int a=0;a<2;++a)for(int rep=0;rep<repeats;++rep){
    const auto& e=endpoints[(b*2+a)*repeats+rep];
    collapse<<b<<','<<(a==0?"bpf":"etpf")<<','<<rep<<','<<e[0]<<','<<e[1]<<'\n';
  }
  const std::array<std::string,3> stages={"all","early_1_100","late_101_1000"};
  std::ofstream summary(dir/"summary.csv"),by_path(dir/"by_path.csv"),timeline(dir/"curves.csv");
  summary<<std::setprecision(17)<<"stage,algorithm,metric,estimate,path_SE\n";
  by_path<<std::setprecision(17)<<"path,stage,algorithm,metric,estimate\n";
  timeline<<std::setprecision(17)<<"step,algorithm,metric,estimate\n";
  for(int st=0;st<3;++st)for(int a=0;a<2;++a)for(int q=0;q<COUNT;++q){
    Moment m;for(int b=0;b<paths;++b){const Real v=results[(b*2+a)*3+st][q];m.add(v);
      by_path<<b<<','<<stages[st]<<','<<(a==0?"bpf":"etpf")<<','<<metric_names[q]<<','<<v<<'\n';}
    summary<<stages[st]<<','<<(a==0?"bpf":"etpf")<<','<<metric_names[q]<<','<<m.mean<<','<<m.se()<<'\n';
  }
  for(int k=0;k<steps;++k)for(int a=0;a<2;++a)for(int q=0;q<COUNT;++q){
    Real mean=0;for(int b=0;b<paths;++b)mean+=curves[(b*2+a)*steps+k][q]/paths;
    timeline<<k+1<<','<<(a==0?"bpf":"etpf")<<','<<metric_names[q]<<','<<mean<<'\n';
  }
  auto max=[](const std::vector<Real>& x){return *std::max_element(x.begin(),x.end());};
  pf::require(max(max_identity)<1e-12L&&max(max_first)==0&&max(max_delta)<1e-11L,"decomposition or pairing failed");
  std::ofstream check(dir/"checks.json");check<<std::setprecision(17)
   <<"{\n  \"reference_mean_refinement\": "<<ref_mean_change
   <<",\n  \"reference_variance_refinement\": "<<ref_variance_change
   <<",\n  \"max_decomposition_residual\": "<<max(max_identity)
   <<",\n  \"max_first_step_pair_difference\": "<<max(max_first)
   <<",\n  \"max_etpf_centroid_defect\": "<<max(max_delta)
   <<",\n  \"max_transport_marginal_residual\": "<<max(max_marginal)<<"\n}\n";
  std::cout<<"Completed "<<paths<<" paths x "<<repeats<<" repeats x "<<steps<<" steps x 2 algorithms\n";
}

int main(int argc,char**argv){
  pf::require(argc==4,"experiment generate|calculate output_directory reflect|reject");
  boundary=argv[3];pf::require(boundary=="reflect"||boundary=="reject","invalid boundary rule");
  pf::require(std::abs(reflect(.2)-.2)<1e-14 && std::abs(reflect(-.2)-.2)<1e-14 &&
              std::abs(reflect(1.2)-.8)<1e-14 && reflect(0)==0 && reflect(1)==1,"reflection identity failed");
  fs::path dir=argv[2];fs::create_directories(dir);
  if(std::string(argv[1])=="generate")generate(dir);
  else if(std::string(argv[1])=="calculate")calculate(dir);
  else throw std::runtime_error("unknown mode");
}
