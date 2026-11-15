// Replays exactly the existing 64 x 32 ETPF runs; no new seeds or repetitions.
// Renamed archived main is not invoked; only its Filter/model definitions are reused.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wreturn-type"
#define main archived_experiment_main
#include "experiment.cpp"
#undef main
#pragma GCC diagnostic pop

int main(int argc,char**argv){
  pf::require(argc==2,"joint_moments runs_directory");
  boundary="reflect";const fs::path dir=argv[1];
  std::vector<double> observations(paths*steps);
  std::ifstream data(dir/"data.csv");std::string line;std::getline(data,line);int seen=0;
  while(std::getline(data,line)){
    std::replace(line.begin(),line.end(),',',' ');std::istringstream row(line);int b,k;double t,y;
    row>>b>>k>>t>>y;observations[b*steps+k-1]=y;++seen;
  }
  pf::require(seen==paths*steps,"data size mismatch");
  using Parts=std::array<Real,3>;
  std::vector<Parts> per_path(paths*3),curves(paths*steps);
  std::vector<Real> max_residual(paths);
  #pragma omp parallel for schedule(dynamic)
  for(int b=0;b<paths;++b){
    std::vector<Real> particle_mean(steps*particles),diagonal_m2(steps),off_diagonal_m2(steps);
    std::vector<Moment> centroid(steps);
    for(int rep=0;rep<repeats;++rep){
      Filter f(b,rep,true);
      for(int k=0;k<steps;++k){
        const auto out=f.step(observations[b*steps+k]);centroid[k].add(out.post);
        Real prefix=0,diagonal=0,off=0;
        for(int i=0;i<particles;++i){
          auto& mean=particle_mean[k*particles+i];const Real delta=Real(f.x(0,i))-mean;
          mean+=delta/(rep+1);
          diagonal+=delta*delta;
          off+=2*delta*prefix; // directly accumulates both ordered off-diagonal products
          prefix+=delta;
        }
        diagonal_m2[k]+=Real(rep)/(rep+1)*diagonal;
        off_diagonal_m2[k]+=Real(rep)/(rep+1)*off;
      }
    }
    for(int k=0;k<steps;++k){
      const Real diagonal=diagonal_m2[k]/(repeats-1)/(particles*particles);
      const Real off=off_diagonal_m2[k]/(repeats-1)/(particles*particles);
      const Real total=centroid[k].variance();curves[b*steps+k]={diagonal,off,total};
      max_residual[b]=std::max(max_residual[b],std::abs(diagonal+off-total));
      for(int st=0;st<3;++st){
        if((st==1&&k>=100)||(st==2&&k<100))continue;
        const int width=st==0?steps:st==1?100:steps-100;
        for(int q=0;q<3;++q)per_path[b*3+st][q]+=curves[b*steps+k][q]/width;
      }
    }
  }
  std::ofstream summary(dir/"joint_moments.csv"),paths_out(dir/"joint_moments_by_path.csv"),timeline(dir/"joint_moments_curves.csv");
  summary<<std::setprecision(20)<<"stage,diagonal_contribution,off_diagonal_contribution,algorithm_fluctuation,diagonal_path_SE,off_diagonal_path_SE,total_path_SE\n";
  paths_out<<std::setprecision(20)<<"path,stage,diagonal_contribution,off_diagonal_contribution,algorithm_fluctuation\n";
  timeline<<std::setprecision(20)<<"step,diagonal_contribution,off_diagonal_contribution,algorithm_fluctuation\n";
  const std::array<std::string,3> stage={"all","early_1_100","late_101_1000"};
  for(int st=0;st<3;++st){
    std::array<Moment,3> moments;
    for(int b=0;b<paths;++b){
      paths_out<<b<<','<<stage[st];
      for(int q=0;q<3;++q){const auto v=per_path[b*3+st][q];moments[q].add(v);paths_out<<','<<v;}
      paths_out<<'\n';
    }
    summary<<stage[st];for(const auto& m:moments)summary<<','<<m.mean;for(const auto& m:moments)summary<<','<<m.se();summary<<'\n';
  }
  for(int k=0;k<steps;++k){
    Parts mean{};for(int b=0;b<paths;++b)for(int q=0;q<3;++q)mean[q]+=curves[b*steps+k][q]/paths;
    timeline<<k+1;for(auto v:mean)timeline<<','<<v;timeline<<'\n';
  }
  const Real error=*std::max_element(max_residual.begin(),max_residual.end());
  pf::require(error<1e-14L,"particle inner-product decomposition failed");
  std::ofstream check(dir/"joint_moments_checks.json");
  check<<std::setprecision(20)<<"{\"max_step_decomposition_residual\": "<<error<<"}\n";
  std::cout<<"Same-run particle inner products verified; max residual "<<double(error)<<'\n';
}
